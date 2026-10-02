"""Compile real command history methods against an engine double (x86 cl)."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/prediction.cpp").read_text()
methods = source[source.index("void Prediction::store_data("):source.index("void Prediction::end(")]
methods += source[source.index("void Prediction::store_netvars("):source.index("void Prediction::detect_prediction_error(")]
header = (root / "features/prediction.h").read_text()
netvars = header[header.index("struct NetvarsData"):header.index("struct TickbaseData")]
header = (root / "sdk/interfaces/CInput.hpp").read_text()
begin = header.index("CUserCmd* GetUserCmd(")
get_cmd = header[begin:header.index("\n\t}", begin) + len("\n\t}")]

stub = r"""
#include <cassert>
#include <algorithm>
#include <cmath>
#include <cfloat>
#include <climits>
using std::clamp;
using std::abs;
template<class T> struct crypt_ptr {
    T* p=nullptr;
    crypt_ptr(T* value=nullptr):p(value){}
    T* get() const {return p;}
    T* operator->() const {return p;}
    explicit operator bool() const {return p!=nullptr;}
};
struct Vector {
    float x=0,y=0,z=0;
    Vector operator-(const Vector& v) const {return {x-v.x,y-v.y,z-v.z};}
    float DistToSqr(const Vector& v) const {auto d=*this-v; return d.x*d.x+d.y*d.y+d.z*d.z;}
};
constexpr int MULTIPLAYER_BACKUP=150, WEAPON_REVOLVER=64;
struct CUserCmd {int command_number=0,buttons=0; bool predicted=false;};
struct Weapon {int type=WEAPON_REVOLVER; float postpone=77;
    int m_iItemDefinitionIndex(){return type;}
    float& m_flPostponeFireReadyTime(){return postpone;}
};
struct Handle {int value=123; int ToInt(){return value;}};
struct Player {
    float spawn=1,modifier=1,duck=0;
    int flags=1,type=2,tickbase=100;
    Vector origin,velocity,view_offset{0,0,64},punch,punch_vel,view_punch;
    Handle handle;
    float m_flSpawnTime(){return spawn;}
    Handle& m_hActiveWeapon(){return handle;}
    int m_fFlags(){return flags;} int m_moveType(){return type;}
    float m_flDuckAmount(){return duck;}
    float& m_flVelocityModifier(){return modifier;}
    Vector& m_vecVelocity(){return velocity;}
    Vector& m_vecLastPredictedPosition(){return origin;}
    Vector& m_vecOrigin(){return origin;}
    Vector& m_vecViewOffset(){return view_offset;}
    Vector& m_aimPunchAngle(){return punch;}
    Vector& m_aimPunchAngleVel(){return punch_vel;}
    Vector& m_viewPunchAngle(){return view_punch;}
    int m_nTickBase(){return tickbase;}
    int m_fEffects(){return 0;}
    int m_ubEFNoInterpParity(){return 0;}
    int m_ubEFNoInterpParityOld(){return 0;}
};
struct Context {
    Player player; Weapon gun; Weapon* current=&gun; int last_predicted_command=9;
    crypt_ptr<Player> local(){return &player;}
    crypt_ptr<Weapon> weapon(){return current;}
} context;
auto ctx=&context;
struct Config {struct {bool enable=true;} rage;} config_state;
auto config=&config_state;
struct ClientState {int m_nLastCommandAck=0,m_nDeltaTick=1;} client_state;
auto clientstate=&client_state;
struct EnginePrediction {int m_nPreviousStartFrame=1,updates=0;
    void Update(int,bool,int,int){++updates;}
} engine_state;
auto prediction=&engine_state;
struct Exploits {float last_exploit_time=0;} exploit_state;
auto exploits=&exploit_state;
struct Globals {float realtime=10;} globals_state;
auto globals=&globals_state;
struct Input {CUserCmd* m_pCommands=nullptr;
""" + get_cmd + r"""
} input_state;
crypt_ptr<Input> input=&input_state;
""" + netvars + r"""
class Prediction {public:
    int flags=0,move_type=0,buttons=0;
    float duck_amount=0,velocity_modifier=0;
    Vector velocity,origin;
    NetvarsData netvars_data[MULTIPLAYER_BACKUP];
    void store_data(crypt_ptr<CUserCmd>);
    void store_netvars(int);
    void restore_netvars(int);
};
"""

checks = r"""
int main(){
    Prediction p;
    CUserCmd cmd,commands[MULTIPLAYER_BACKUP];
    assert(!input->GetUserCmd(1));
    input->m_pCommands=commands;
    assert(!input->GetUserCmd(-1));
    assert(input->GetUserCmd(150)==&commands[0]);
    p.store_data(nullptr);
    cmd.command_number=INT_MIN; p.store_data(&cmd);
    p.store_netvars(-1); p.restore_netvars(-1);
    p.store_netvars(0); assert(p.netvars_data[0].m_command_number==-1);
    cmd.command_number=1; p.store_data(&cmd);
    assert(ctx->gun.postpone==77); // Default ring slot is not a snapshot.
    cmd.command_number=10;
    input->m_pCommands=nullptr; p.store_data(&cmd);
    input=nullptr; p.store_data(&cmd);
    input=&input_state; input->m_pCommands=commands;
    commands[9].command_number=9;
    p.store_netvars(9); ctx->gun.postpone=88;
    p.store_data(&cmd); assert(ctx->gun.postpone==77);
    commands[9].command_number=159;
    ctx->gun.postpone=88; p.store_data(&cmd); assert(ctx->gun.postpone==88);
    commands[9].command_number=9;
    ++ctx->player.handle.value;
    p.store_data(&cmd); p.restore_netvars(9); assert(ctx->gun.postpone==88);
    --ctx->player.handle.value;
    ctx->gun.type=1; p.store_data(&cmd); p.restore_netvars(9); assert(ctx->gun.postpone==88);
    ctx->gun.type=WEAPON_REVOLVER; ctx->current=nullptr;
    p.store_data(&cmd); p.restore_netvars(9);
    ctx->current=&ctx->gun;
    ++ctx->player.spawn;
    p.store_data(&cmd); p.restore_netvars(9); assert(ctx->gun.postpone==88);
    --ctx->player.spawn;
    p.netvars_data[9].player=nullptr;
    p.store_data(&cmd); p.restore_netvars(9); assert(ctx->gun.postpone==88);
    p.netvars_data[9].player=ctx->local().get();
    config->rage.enable=false;
    p.store_data(&cmd); p.restore_netvars(9); assert(ctx->gun.postpone==88);
    config->rage.enable=true;
    p.restore_netvars(9); assert(ctx->gun.postpone==77);
    commands[9].predicted=true;
    int updates=prediction->updates;
    p.store_data(&cmd); assert(prediction->updates==updates);
    ++ctx->player.spawn;
    p.store_data(&cmd); assert(prediction->updates==updates+1);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "command_history.cpp"
    cpp.write_text(stub + methods + checks)
    exe = directory / "command_history.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Command history checks passed")
