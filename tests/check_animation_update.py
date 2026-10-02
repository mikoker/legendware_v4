"""Check the real animation update wrapper with an engine double (x86 cl)."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "sdk/classes.cpp").read_text()
method = source[source.index("void Player::update_animations("):source.index("void Player::invalidate_physics_recursive(")]
stub = r"""
#include <cassert>
#include <algorithm>
struct AnimationState {float last_update_time=10; int last_update_frame=100;};
struct Vector {float x=0,y=0,z=0;};
template<class T> struct crypt_ptr {T* p; T* operator->(){return p;} explicit operator bool(){return p!=nullptr;}};
struct Globals {float curtime=10,intervalpertick=.015625f; int framecount=100;} global_state;
auto globals=&global_state;
struct Context {bool updating_animation=false;} context;
auto ctx=&context;
constexpr int EFL_DIRTY_ABSVELOCITY=0x1000,INDEX_UPDATE_CLIENTSIDE_ANIMATION=224;
class Player {public:
    AnimationState state; bool alive=true,prepared=true,has_state=true,hltv=false;
    float snapshot1=2,snapshot2=3,last_delta=0;
    int flags=EFL_DIRTY_ABSVELOCITY,calls=0;
    Vector abs_velocity,velocity;
    bool valid(){return alive;}
    crypt_ptr<AnimationState> get_animation_state(){return {has_state?&state:nullptr};}
    bool force_animations_data(){return prepared;}
    float& m_BoneSnapshotFirst(){return snapshot1;}
    float& m_BoneSnapshotSecond(){return snapshot2;}
    int& m_iEFlags(){return flags;}
    bool& m_bIsHLTV(){return hltv;}
    Vector& m_vecAbsVelocity(){return abs_velocity;}
    Vector& m_vecVelocity(){return velocity;}
    void update_animations();
};
void __fastcall engine_update(void* object, void*){
    auto p=static_cast<Player*>(object);
    assert(ctx->updating_animation && p->hltv);
    assert(p->snapshot1==1 && p->snapshot2==1);
    assert((p->flags&EFL_DIRTY_ABSVELOCITY)==0);
    assert(p->state.last_update_frame!=globals->framecount);
    p->last_delta=std::max(0.0f,globals->curtime-p->state.last_update_time);
    p->state.last_update_time=globals->curtime;
    p->state.last_update_frame=globals->framecount;
    ++p->calls;
}
template<class T> T call_virtual(void*,int){return reinterpret_cast<T>(&engine_update);}
"""
checks = r"""
int main(){
    Player p;
    p.update_animations();
    assert(p.calls==1 && p.last_delta==globals->intervalpertick);
    assert(!ctx->updating_animation && !p.hltv);
    assert(p.snapshot1==2 && p.snapshot2==3 && p.flags==EFL_DIRTY_ABSVELOCITY);
    ctx->updating_animation=true;
    p.update_animations();
    assert(p.calls==2 && p.last_delta==globals->intervalpertick);
    assert(ctx->updating_animation);
    p.prepared=false;
    p.update_animations();
    assert(p.calls==2 && p.state.last_update_time==10 && p.state.last_update_frame==100);
    assert(ctx->updating_animation && !p.hltv && p.snapshot1==2 && p.snapshot2==3);
    p.prepared=true; p.alive=false; p.update_animations(); assert(p.calls==2);
    p.alive=true; p.has_state=false; p.update_animations(); assert(p.calls==2);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "animation_update.cpp"
    cpp.write_text(stub + method + checks)
    exe = directory / "animation_check.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Animation update checks passed")
