"""Compile real knife trace and fire methods with an x86 engine double."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/knife_aim.cpp").read_text()
methods = source[source.index("static bool trace_knife_attack("):]
stub = r"""
#include <cassert>
#include <algorithm>
#include <cmath>
#include <vector>
using std::clamp;
#define BETA 0
constexpr int IN_ATTACK=1,IN_ATTACK2=2048,FL_FROZEN=32,MASK_SOLID=0x200400B;
template<class T> struct crypt_ptr {T* p=nullptr; crypt_ptr(T* v=nullptr):p(v){} T* get(){return p;} T* operator->(){return p;} explicit operator bool(){return p!=nullptr;}};
struct Vector {
    float x=0,y=0,z=0; Vector()=default; Vector(float a,float b,float c):x(a),y(b),z(c){}
    Vector operator+(Vector v)const{return {x+v.x,y+v.y,z+v.z};}
    Vector operator-(Vector v)const{return {x-v.x,y-v.y,z-v.z};}
    Vector operator*(float f)const{return {x*f,y*f,z*f};}
    void operator/=(float f){x/=f;y/=f;z/=f;}
    float Length()const{return std::sqrt(x*x+y*y+z*z);}
    void NormalizeInPlace(){auto l=Length();if(l>0)*this/=l;}
    float Dot(Vector v)const{return x*v.x+y*v.y+z*v.z;}
    Vector ToEulerAngles(){return {std::atan2(-z,std::sqrt(x*x+y*y))*180/3.14159265f,std::atan2(y,x)*180/3.14159265f,0};}
};
namespace math {void angle_vectors(Vector a,Vector* f,void*,void*){float y=a.y*3.14159265f/180;*f={std::cos(y),std::sin(y),0};}}
struct CUserCmd {int buttons=0,tickcount=0; Vector viewangles;};
struct Player {int flags=0,health=100,armor=0; float next_attack=0; Vector origin;
    int m_fFlags(){return flags;} float m_flNextAttack(){return next_attack;}
    int m_iHealth(){return health;} int m_ArmorValue(){return armor;}
    Vector m_vecOrigin(){return origin;}
};
struct Weapon {float primary=0,secondary=0;
    float m_flNextPrimaryAttack(){return primary;} float m_flNextSecondaryAttack(){return secondary;}
};
struct Context {Player player; Weapon gun; bool has_weapon=true; int tickbase=640; float interpolation=0; Vector shoot_position;
    crypt_ptr<Player> local(){return &player;} crypt_ptr<Weapon> weapon(){return has_weapon?&gun:nullptr;}
} context;
auto ctx=&context;
struct Globals {float intervalpertick=1.f/64;} global_state;
auto globals=&global_state;
#define TICKS_TO_TIME(t) ((t)*globals->intervalpertick)
#define TIME_TO_TICKS(t) ((int)(.5f+(t)/globals->intervalpertick))
struct Config {struct {bool automatic_fire=true,silent=true;} rage;} config_state;
auto config=&config_state;
struct Engine {void SetViewAngles(Vector){}} engine_state;
auto engine=&engine_state;
struct Record {Vector origin{40,0,0},mins{-16,-16,-18},maxs{16,16,18},abs_angles{0,180,0}; float simulation_time=9; bool ready=true;
    bool apply(){return ready;}
};
struct Target {crypt_ptr<Player> player; crypt_ptr<Record> data;};
class KnifeAim {public:Target final_target; void fire(crypt_ptr<CUserCmd>);};
struct CTraceFilter {Player* pSkip=nullptr;};
struct CGameTrace {float fraction=1; Player* hit_entity=nullptr;};
struct Ray_t {Vector start,end,mins,maxs; bool hull=false;
    void Init(Vector s,Vector e){start=s;end=e;hull=false;}
    void Init(Vector s,Vector e,Vector mi,Vector ma){start=s;end=e;mins=mi;maxs=ma;hull=true;}
};
struct TraceEngine {Player* target=nullptr; bool wall=false; float distance=24; std::vector<Ray_t> rays;
    void TraceRay(Ray_t ray,int mask,CTraceFilter* filter,CGameTrace* trace){
        assert(mask==MASK_SOLID && filter->pSkip==ctx->local().get()); rays.push_back(ray);
        trace->hit_entity=nullptr; trace->fraction=1;
        if(wall){trace->fraction=.2f;return;}
        if((ray.end-ray.start).Length()+(ray.hull?16:0)>=distance){trace->fraction=.5f;trace->hit_entity=target;}
    }
} trace_state;
auto enginetrace=&trace_state;
"""
checks = r"""
int main(){
    Player enemy; Record record; KnifeAim aim; CUserCmd cmd;
    aim.final_target.player=&enemy; aim.final_target.data=&record; enginetrace->target=&enemy;
    assert(trace_knife_attack(&enemy,{100,0,0},true));
    assert(enginetrace->rays.size()==1 && enginetrace->rays.back().end.x==32);
    enginetrace->rays.clear(); enginetrace->distance=60;
    assert(trace_knife_attack(&enemy,{100,0,0},false));
    assert(enginetrace->rays.size()==2 && enginetrace->rays[0].end.x==48);
    assert(enginetrace->rays[1].hull && enginetrace->rays[1].mins.z==-18 && enginetrace->rays[1].maxs.x==16);
    enginetrace->rays.clear(); enginetrace->wall=true;
    assert(!trace_knife_attack(&enemy,{100,0,0},true)); assert(enginetrace->rays.size()==1);
    enginetrace->rays.clear(); assert(!trace_knife_attack(&enemy,{},true));
    assert(!trace_knife_attack(&enemy,{NAN,0,0},true)); assert(enginetrace->rays.empty());
    enginetrace->wall=false; enginetrace->distance=24;
    enemy.health=30; aim.fire(&cmd); assert(cmd.buttons==IN_ATTACK && cmd.tickcount==576);
    // A ready stab remains usable when primary cooldown is still active.
    cmd={}; cmd.buttons=IN_ATTACK2; ctx->gun.primary=11;
    aim.fire(&cmd); assert(cmd.buttons==IN_ATTACK2 && cmd.tickcount==576);
    cmd={}; cmd.buttons=IN_ATTACK|IN_ATTACK2;
    aim.fire(&cmd); assert(cmd.buttons==(IN_ATTACK|IN_ATTACK2) && cmd.tickcount==576);
    cmd={}; cmd.buttons=IN_ATTACK;
    aim.fire(&cmd); assert(cmd.buttons==IN_ATTACK && cmd.tickcount==0);
    cmd={}; cmd.buttons=IN_ATTACK2; ctx->gun.secondary=11;
    aim.fire(&cmd); assert(cmd.tickcount==0);
    // Automatic preferred stab can fall back to a ready, reachable swing.
    ctx->gun.primary=0; enemy.health=60; cmd={}; aim.fire(&cmd); assert(cmd.buttons==IN_ATTACK);
    ctx->gun.secondary=0; cmd={}; aim.fire(&cmd); assert(cmd.buttons==IN_ATTACK2);
    cmd={}; enginetrace->wall=true; aim.fire(&cmd); assert(cmd.buttons==0 && cmd.tickcount==0);
    enginetrace->wall=false; ctx->player.flags=FL_FROZEN; cmd={}; aim.fire(&cmd); assert(cmd.buttons==0);
    ctx->player.flags=0; ctx->player.next_attack=11; aim.fire(&cmd); assert(cmd.buttons==0);
    ctx->player.next_attack=0; config->rage.automatic_fire=false; aim.fire(&cmd); assert(cmd.buttons==0);
    config->rage.automatic_fire=true; record.ready=false; aim.fire(&cmd); assert(cmd.buttons==0);
    record.ready=true; ctx->has_weapon=false; aim.fire(&cmd); assert(cmd.buttons==0);
    aim.fire(nullptr);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "knife_check.cpp"
    cpp.write_text(stub + methods + checks)
    exe = directory / "knife_check.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Knife checks passed")
