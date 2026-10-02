"""Exercise production visual bone builder/failure handling and cache publication."""
import ast
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
# Reuse the same minimal engine double without executing its test runner.
tree = ast.parse((root / "tests/check_bone_cache.py").read_text())
stub = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "stub" for t in n.targets))
stub = "bool rebuild_success=false, engine_success=false;\n" + stub
stub = stub.replace("void Zero() { x=y=z=0; }", "void Zero() { x=y=z=0; } bool operator!=(const Vector& v) const { return x!=v.x || y!=v.y || z!=v.z; }")
stub = stub.replace("float m[3][4];", "float m[3][4]; float* operator[](int i) { return m[i]; }")
stub = stub.replace("bool valid() {", "void invalidate_physics_recursive(int) {} void attachment_helper() {} bool setup_bones_rebuilded(int,matrix3x4_t*) { return rebuild_success; } bool setup_bones(matrix3x4_t* out,int mask) { if(engine_success) { accessor.m_ReadableBones=mask|0x80000; out[0].m[0][3]=10; } return engine_success; } bool valid() {")
stub = stub.replace("bool setuping_bones=false;", "bool setuping_bones=false,updating_animation=false;")
header = (root / "features/animations.h").read_text()
record = header[header.index("class AnimationData"):header.index("\tvirtual bool valid(")] + "};\n"
source = (root / "features/animations.cpp").read_text()
builder = source[source.index("\tauto setup_matrix ="):source.index("\tauto roll =", source.index("\tauto setup_matrix ="))]
start = source.index("\tif (data->matrix_ready & (1u << MATRIX_VISUAL_INTERPOLATED))")
publish = source[start:source.index("\tglobals->curtime = backup_curtime;", start)]
hook = (root / "hooks/hooked_updateclientsideanimation.cpp").read_text()
hook = hook[hook.index("void __fastcall hooked_updateclientsideanimation("):]
cpp = stub + (root / "features/bone_cache.h").read_text() + record + r"""
#include <deque>
struct AnimationsDouble { std::deque<AnimationData> animation_data[65]; } animations_instance;
auto animations=&animations_instance;
struct LocalDouble { void render() {} } local_instance;
auto local_animations=&local_instance;
using UpdateClientSideAnimation=void(__thiscall*)(Player*);
int update_calls=0;
void __fastcall mock_update(Player*,void*) { ++update_calls; }
uintptr_t original_updateclientsideanimation=reinterpret_cast<uintptr_t>(&mock_update);
""" + hook + r"""
int main() {
    Player local,player;ctx->player=&local;entities.target=&player;
    auto& front=animations->animation_data[1].emplace_back(1);
    front.store(&player,false);
    front.bone_count=2;
    auto data=crypt_ptr<AnimationData>(&front);
""" + builder + r"""
    setup_matrix(&player,data,MATRIX_VISUAL_INTERPOLATED,0);
    assert(!(front.matrix_ready & (1u<<MATRIX_VISUAL_INTERPOLATED)));
""" + publish + r"""
    assert(!(front.matrix_ready & (1u<<MATRIX_VISUAL)));
    player.bones.data[0].m[0][3]=99;
    hooked_updateclientsideanimation(&player,nullptr);
    assert(update_calls==1 && player.bones.data[0].m[0][3]==99);
    engine_success=true;
    setup_matrix(&player,data,MATRIX_VISUAL_INTERPOLATED,0);
    assert(front.matrix_ready & (1u<<MATRIX_VISUAL_INTERPOLATED));
    assert(front.matrix_mask[MATRIX_VISUAL_INTERPOLATED]==(BONE_USED_BY_ANYTHING|0x80000));
""" + publish + r"""
    assert(front.matrix_ready & (1u<<MATRIX_VISUAL));
    assert(front.matrix[MATRIX_VISUAL][0].m[0][3]==10);
    // Publishing must work at unchanged origins and with an empty old cache.
    player.bones.m_Size=0;
    hooked_updateclientsideanimation(&player,nullptr);
    assert(update_calls==1 && player.bones.m_Size==2 && player.bones.data[0].m[0][3]==10);
    assert(player.accessor.m_ReadableBones==(BONE_USED_BY_ANYTHING|0x80000));
    player.absorigin.x=5;
    hooked_updateclientsideanimation(&player,nullptr);
    assert(front.matrix[MATRIX_VISUAL_INTERPOLATED][0].m[0][3]==15);
    assert(front.matrix[MATRIX_VISUAL][0].m[0][3]==10);
    // A render hook cannot overwrite an active historical transaction.
    historical_bone_cache[1]={&player,BONE_USED_BY_HITBOX,player.spawn,player.model};
    player.bones.data[0].m[0][3]=42;front.matrix_ready=0;
    hooked_updateclientsideanimation(&player,nullptr);
    assert(update_calls==1 && player.bones.data[0].m[0][3]==42);
    historical_bone_cache[1]={};
    animations->animation_data[1].clear();
    hooked_updateclientsideanimation(&player,nullptr);
    assert(update_calls==2);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    path = directory / "visual_bones.cpp"
    path.write_text(cpp)
    exe = directory / "visual_bones.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(path), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Visual bone checks passed")
