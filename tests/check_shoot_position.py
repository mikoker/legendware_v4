"""Check real prediction shooting bones and eye adjustment using x86 cl."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/prediction.cpp").read_text()
method = source[source.index("void Prediction::update_data("):source.index("void Prediction::store_data(")]
source = (root / "sdk/classes.cpp").read_text()
method += source[source.index("Vector Player::get_shoot_position()"):source.index("Vector& Player::third_person_angles()")]
header = (root / "features/local_animations.h").read_text()
begin = header.index("bool has_shoot_pose(")
has_pose = header[begin:header.index("\n\t}", begin) + len("\n\t}")]

stub = r"""
#include <cassert>
#include <cmath>
#include <cfloat>
#include <cstring>
#include <algorithm>
constexpr int MAXSTUDIOBONES=128,BONE_USED_BY_HITBOX=256,SIGNATURE_LOOKUP_BONE=0;
using matrix3x4_t=float[3][4];
template<class T> struct crypt_ptr {T* p=nullptr; crypt_ptr(T* v=nullptr):p(v){} T* get(){return p;} T* operator->(){return p;} explicit operator bool(){return p!=nullptr;}};
struct Vector {
    float x=0,y=0,z=0; Vector()=default; Vector(float a,float b,float c):x(a),y(b),z(c){}
    Vector operator+(Vector v){return {x+v.x,y+v.y,z+v.z};}
    Vector operator-(Vector v){return {x-v.x,y-v.y,z-v.z};}
    float LengthSqr(){return x*x+y*y+z*z;}
};
namespace math {
float lerp(float a,float b,float f){return a+(b-a)*f;}
float simple_spline_remap_val_clamped(float v,float a,float b,float c,float d){float f=std::clamp((v-a)/(b-a),0.f,1.f); return c+(d-c)*f*f*(3-2*f);}
}
#define crypt_str(s) s
struct AnimationLayer {float value=0;};
struct AnimationState {bool landing=false; float duck_amount=1;};
struct Cache {int Count(){return 5;}};
struct Accessor {int m_ReadableBones=1,m_WritableBones=1;};
class Player {public:
    bool alive=true,succeed=true,has_layers=true; int layer_count=13,calls=0,counter=1;
    float spawn=1,last_time=0,poses[24]{}; float observed_pose=0;
    const void* model=(void*)1;
    Vector angles{1,2,3},origin,view_offset{0,0,64};
    AnimationLayer layers[13]; AnimationState state; Cache cache; Accessor accessor;
    bool valid(){return alive;} float m_flSpawnTime(){return spawn;}
    const void* GetModel(){return model;}
    int get_animation_layers_count(){return layer_count;}
    crypt_ptr<AnimationLayer> get_animation_layer(){return has_layers?layers:nullptr;}
    float* m_flPoseParameters(){return poses;}
    Vector GetAbsAngles(){return angles;} void set_abs_angles(Vector a){angles=a;}
    Vector& m_vecOrigin(){return origin;} Vector& m_vecViewOffset(){return view_offset;}
    crypt_ptr<AnimationState> get_animation_state(){return &state;}
    Cache& m_CachedBoneData(){return cache;} Accessor& m_BoneAccessor(){return accessor;}
    int& m_iMostRecentModelBoneCounter(){return counter;}
    float& m_flLastBoneSetupTime(){return last_time;}
    bool setup_bones(crypt_ptr<matrix3x4_t> out,int){
        ++calls; assert(angles.x==0 && angles.y==0 && poses[12]==.5f);
        observed_pose=poses[0]; accessor.m_ReadableBones=256; accessor.m_WritableBones=256;
        if(succeed){out.get()[2][2][3]=origin.z+30; return true;} return false;
    }
    Vector get_shoot_position(); void modify_shoot_position(Vector&);
};
struct Weapon {void update_accuracy_penalty(){} float get_spread(){return .1f;} float get_inaccuracy(){return .2f;}};
struct Context {
    Player player; Weapon gun; bool with_weapon=true,prediction_bones_ready=false;
    float spread=0,inaccuracy=0,prediction_bone_spawn=0;
    Player* prediction_bone_player=nullptr; const void* prediction_bone_model=nullptr;
    int prediction_bone_count=0; Vector prediction_bone_origin,shoot_position;
    matrix3x4_t prediction[MAXSTUDIOBONES]{};
    crypt_ptr<Player> local(){return &player;} crypt_ptr<Weapon> weapon(){return with_weapon?&gun:nullptr;}
} context;
auto ctx=&context;
struct LocalAnimations {float pose_parameters_shoot[24]{}; AnimationLayer layers_shoot[13]{};
    Player* shoot_player=nullptr; float shoot_spawn=0; const void* shoot_model=nullptr; int shoot_layer_count=0;
""" + has_pose + r"""
} local_state;
auto local_animations=&local_state;
int head_index=2;
int __fastcall lookup_bone(void*,void*,const char*){return head_index;}
struct Signatures {void* signatures[1]={(void*)&lookup_bone};} signature_state;
auto signatures_manager=&signature_state;
class Prediction {public: void update_data(); void store_viewmodel(){}};
"""
checks = r"""
int main(){
    Prediction p; auto& player=ctx->player;
    player.poses[0]=3; player.poses[12]=.8f; player.layers[0].value=4;
    p.update_data();
    assert(player.observed_pose==3); // No shoot snapshot yet: keep current pose.
    assert(ctx->prediction_bones_ready && ctx->prediction_bone_count==5);
    assert(player.poses[0]==3 && player.poses[12]==.8f && player.layers[0].value==4);
    assert(player.angles.x==1 && player.angles.y==2 && player.angles.z==3);
    assert(player.accessor.m_ReadableBones==0 && player.accessor.m_WritableBones==0 && player.last_time==-FLT_MAX);
    assert(ctx->shoot_position.z<64);
    local_state.shoot_player=&player; local_state.shoot_spawn=player.spawn;
    local_state.shoot_model=player.model; local_state.shoot_layer_count=13;
    local_state.pose_parameters_shoot[0]=9;
    p.update_data(); assert(player.observed_pose==9 && player.poses[0]==3);
    player.succeed=false; p.update_data();
    assert(!ctx->prediction_bones_ready && ctx->shoot_position.z==64);
    assert(player.angles.y==2 && player.poses[12]==.8f);
    player.succeed=true; ++player.spawn; p.update_data(); assert(player.observed_pose==3);
    ++player.spawn; assert(player.get_shoot_position().z==64);
    p.update_data(); player.model=(void*)2; assert(player.get_shoot_position().z==64);
    p.update_data(); ++player.origin.x; assert(player.get_shoot_position().z==64);
    p.update_data(); head_index=-1; assert(player.get_shoot_position().z==64);
    head_index=5; assert(player.get_shoot_position().z==64);
    head_index=128; assert(player.get_shoot_position().z==64);
    head_index=2;
    int calls=player.calls; player.layer_count=14; p.update_data();
    assert(!ctx->prediction_bones_ready && player.calls==calls && ctx->shoot_position.z==64);
    player.layer_count=13; player.has_layers=false; p.update_data(); assert(player.calls==calls);
    player.has_layers=true; ctx->with_weapon=false; p.update_data(); assert(!ctx->prediction_bones_ready);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "shoot_position.cpp"
    cpp.write_text(stub + method + checks)
    exe = directory / "shoot_position.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Shoot position checks passed")
