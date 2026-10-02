"""Exercise real record store/apply and SetupBones hook against an x86 engine double."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
header = (root / "features/animations.h").read_text()
record = header[header.index("class AnimationData"):header.index("\tvirtual bool valid(")] + "};\n"
hook = (root / "hooks/hooked_setupbones.cpp").read_text()
hook = hook[hook.index("bool __fastcall hooked_setupbones("):]
cache = (root / "features/bone_cache.h").read_text()
stub = r"""
#include <cassert>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <cfloat>
template<class T> struct crypt_ptr {
    T* p; crypt_ptr(T* v=nullptr):p(v) {}
    T* get() const { return p; } T* operator->() const { return p; }
    explicit operator bool() const { return p != nullptr; }
};
enum { MATRIX_VISUAL,MATRIX_VISUAL_INTERPOLATED,MATRIX_MAIN,MATRIX_ZERO,MATRIX_FIRST,MATRIX_FIRST_LOW,MATRIX_SECOND,MATRIX_SECOND_LOW,MATRIX_BASELINE,MATRIX_MAX };
enum { LAYERS_ORIGINAL,LAYERS_BASELINE,LAYERS_ZERO,LAYERS_FIRST,LAYERS_SECOND,LAYERS_MAX };
enum { MAXSTUDIOBONES=128, BONE_USED_BY_HITBOX=0x100, BONE_USED_BY_ANYTHING=0x7ff00, RESOLVER_NONE, SIGNATURE_MODIFY_BONES=0, CONVAR_R_JIGGLE_BONES=0 };
struct Vector { float x=0,y=0,z=0; void Zero() { x=y=z=0; } };
struct matrix3x4_t { float m[3][4]; };
struct AnimationLayer { float cycle; };
struct ShortAnimationLayer {};
struct Weapon {};
struct AnimationState { Weapon* weapon=nullptr; Weapon* weapon_last_bone_setup=nullptr; };
struct ResolverResult {};
struct NetworkAnimationSnapshot {};
struct ICollideable { Vector mins,maxs; Vector OBBMins() { return mins; } Vector OBBMaxs() { return maxs; } };
struct BoneAccessor { int m_ReadableBones=0,m_WritableBones=0; };
struct Bones {
    matrix3x4_t data[128]{}; int m_Size=2,capacity=128;
    int Count() const { return m_Size; } int NumAllocated() const { return capacity; }
    matrix3x4_t* Base() { return data; }
};
struct Player {
    int prefix=0; int index=1; bool alive=true; int flags=0,tickbase=100;
    float simtime=2,oldsimtime=1,duck=0,lby=0,collisiontime=0,collisionorigin=0,lastsetup=3,spawn=1;
    const void* model=reinterpret_cast<void*>(1);
    float m_flSpawnTime() { return spawn; } const void* GetModel() { return model; }
    uint32_t recent=4,counter=9; Vector eyes,absangles,velocity,origin,absorigin;
    Bones bones; BoneAccessor accessor; AnimationLayer layers[13]{}; AnimationState anim; ICollideable collision;
    bool valid() { return alive; } int EntIndex() { return index; }
    Bones& m_CachedBoneData() { return bones; } BoneAccessor& m_BoneAccessor() { return accessor; }
    crypt_ptr<AnimationLayer> get_animation_layer() { return layers; } int get_animation_layers_count() { return 13; }
    crypt_ptr<AnimationState> get_animation_state() { return &anim; }
    bool m_bGunGameImmunity() { return false; } bool IsDormant() { return false; }
    bool m_bStrafing() { return false; } bool m_bIsWalking() { return false; }
    int& m_fFlags() { return flags; } float& m_flSimulationTime() { return simtime; }
    float& m_flOldSimulationTime() { return oldsimtime; } float& m_flDuckAmount() { return duck; }
    float& m_flLowerBodyYawTarget() { return lby; } Vector& m_angEyeAngles() { return eyes; }
    Vector GetAbsAngles() { return absangles; } Vector& m_vecVelocity() { return velocity; }
    Vector& m_vecOrigin() { return origin; } Vector GetAbsOrigin() { return absorigin; }
    float& m_flCollisionChangeTime() { return collisiontime; } float& m_flCollisionChangeOrigin() { return collisionorigin; }
    uint32_t& m_iMostRecentModelBoneCounter() { return recent; } uint32_t m_iModelBoneCounter() { return counter; }
    float& m_flLastBoneSetupTime() { return lastsetup; } int m_nTickBase() { return tickbase; }
    ICollideable* GetCollideable() { return &collision; }
    void set_abs_origin(Vector v) { absorigin=v; } void set_abs_angles(Vector v) { absangles=v; }
    void set_collision_bounds(Vector a,Vector b,bool) { collision.mins=a;collision.maxs=b; }
};
struct Entities { Player* target=nullptr; Player* GetClientEntity(int) { return target; } } entities;
auto entitylist=&entities;
struct Globals { float curtime=6; } globals_instance; auto globals=&globals_instance;
#define TICKS_TO_TIME(t) ((t)*0.015625f)
struct Context { bool setuping_bones=false; Player* player=nullptr; crypt_ptr<Player> local() { return player; } } context;
auto ctx=&context;
void __fastcall mock_modify(void*,void*,void*,int) {}
struct Signatures { uintptr_t signatures[1]{ reinterpret_cast<uintptr_t>(&mock_modify) }; } signatures;
auto signatures_manager=&signatures;
struct Convar { int value=1; int GetInt() { return value; } void SetValue(int v) { value=v; } } convar;
struct Convars { Convar* convars[1]{ &convar }; } convars;
auto convars_manager=&convars;
using SetupBones=bool(__thiscall*)(void*,matrix3x4_t*,int,int,float);
int engine_calls=0;
bool __fastcall mock_setup(void*,void*,matrix3x4_t*,int,int,float) { ++engine_calls; return true; }
uintptr_t original_setupbones=reinterpret_cast<uintptr_t>(&mock_setup);
"""
cpp = stub + cache + record + hook + r"""
int main() {
    Player player; entities.target=&player;ctx->player=&player;
    player.accessor.m_ReadableBones=BONE_USED_BY_ANYTHING;
    player.accessor.m_WritableBones=0x200;
    player.bones.data[0].m[0][0]=99;
    AnimationData backup(&player);
    AnimationData record(1);
    record.store(&player,false);
    record.bone_count=2;record.simulation_time=1;
    record.matrix_ready=1u<<MATRIX_MAIN;
    record.matrix_mask[MATRIX_MAIN]=BONE_USED_BY_HITBOX;
    record.matrix[MATRIX_MAIN][0].m[0][0]=42;
    record.apply();
    assert(player.bones.data[0].m[0][0]==42 && player.accessor.m_ReadableBones==BONE_USED_BY_HITBOX);
    void* renderable=reinterpret_cast<char*>(&player)+4;
    matrix3x4_t out[128]{};
    // A frozen historical cache survives global counter changes without engine rebuilds.
    player.counter=10;
    assert(hooked_setupbones(renderable,nullptr,out,2,BONE_USED_BY_HITBOX,3));
    assert(out[0].m[0][0]==42 && engine_calls==0);
    assert(!hooked_setupbones(renderable,nullptr,out,1,BONE_USED_BY_HITBOX,3));
    assert(!hooked_setupbones(renderable,nullptr,out,128,BONE_USED_BY_ANYTHING,3));
    assert(!hooked_setupbones(renderable,nullptr,out,128,-1,3));
    assert(engine_calls==0 && player.bones.data[0].m[0][0]==42);
    assert(hooked_setupbones(renderable,nullptr,nullptr,0,BONE_USED_BY_HITBOX,3));
    // Even an explicit rebuild must not corrupt an active historical transaction.
    ctx->setuping_bones=true;
    assert(!hooked_setupbones(renderable,nullptr,out,128,BONE_USED_BY_ANYTHING,3));
    ctx->setuping_bones=false;
    backup.apply(MATRIX_MAIN,true);
    assert(player.bones.data[0].m[0][0]==99);
    assert(player.accessor.m_ReadableBones==BONE_USED_BY_ANYTHING && player.accessor.m_WritableBones==0x200);
    assert(player.recent==4 && player.lastsetup==3 && historical_bone_cache[1].player==nullptr);
    assert(hooked_setupbones(renderable,nullptr,out,128,-1,3) && engine_calls==1);
    // An unready matrix or undersized engine allocation cannot mutate the player.
    record.matrix_ready=0;record.origin.x=123;
    record.apply();assert(player.origin.x!=123 && historical_bone_cache[1].player==nullptr);
    record.matrix_ready=1u<<MATRIX_MAIN;player.bones.capacity=1;
    record.apply();assert(player.origin.x!=123);
    assert(convar.value==1);
    player.bones.capacity=128;
    // Nested transactions restore the preceding historical cache, then the engine cache.
    assert(record.apply());
    AnimationData nested_backup(&player);
    record.matrix[MATRIX_MAIN][0].m[0][0]=43;
    assert(record.apply());
    assert(nested_backup.apply(MATRIX_MAIN,true));
    assert(player.bones.data[0].m[0][0]==42 && historical_bone_cache[1].player==&player);
    assert(backup.apply(MATRIX_MAIN,true));
    assert(historical_bone_cache[1].player==nullptr);
    // A legitimate empty engine cache can be captured and restored.
    player.bones.m_Size=0;
    AnimationData empty_backup(&player);
    assert(empty_backup.can_apply(MATRIX_MAIN,true));
    assert(record.apply());
    assert(empty_backup.apply(MATRIX_MAIN,true) && player.bones.Count()==0);
    assert(historical_bone_cache[1].player==nullptr);
    // If the allocation changes externally, restore pose and permit engine fallback.
    player.bones.m_Size=2;
    assert(record.apply());
    player.bones.capacity=1;
    assert(!backup.apply(MATRIX_MAIN,true));
    assert(historical_bone_cache[1].player==nullptr && player.accessor.m_ReadableBones==0);
    player.bones.capacity=128;
    player.spawn=2;
    assert(!record.can_apply() && !record.apply());
    player.spawn=1;player.model=reinterpret_cast<void*>(2);
    assert(!record.can_apply() && !record.apply());
    player.model=reinterpret_cast<void*>(1);
    Player replacement;entities.target=&replacement;
    assert(!record.can_apply() && !record.apply());
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    path = directory / "bone_cache.cpp"
    path.write_text(cpp)
    exe = directory / "bone_cache.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(path), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Bone cache checks passed")
