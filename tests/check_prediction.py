"""Compile the real prediction entry/exit methods against a small engine double.

Run from an x86 Visual Studio developer shell: python tests/check_prediction.py
"""
import pathlib
import subprocess
import tempfile


root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/prediction.cpp").read_text()
start = source[source.index("void Prediction::start("):source.index("void Prediction::update_data(")]
end = source[source.index("void Prediction::end("):source.index("void Prediction::store_netvars(")]

stub = r"""
#include <cassert>
#include <algorithm>
#include <climits>
#include <cstdint>
using std::clamp;
template<class T> struct crypt_ptr {
    T* p = nullptr;
    crypt_ptr(T* value = nullptr): p(value) {}
    T* get() const { return p; }
    T* operator->() const { return p; }
    explicit operator bool() const { return p != nullptr; }
};
struct Vector { float z = 0; };
namespace math { Vector normalize_angles(Vector value) { return value; } }
struct CUserCmd { Vector viewangles; float forwardmove=0, sidemove=0, upmove=0; int random_seed=0, command_number=10; };
struct CMoveData {};
struct Collideable { Vector OBBMaxs() { return {}; } };
struct Player {
    CUserCmd* current = nullptr; float modifier = 1; Vector position; Collideable bounds;
    void set_current_command(CUserCmd* cmd) { current = cmd; }
    Collideable* GetCollideable() { return &bounds; }
    int m_nTickBase() { return 100; }
    void UpdateCollisionBounds() {}
    float& m_flVelocityModifier() { return modifier; }
    Vector& m_vecLastPredictedPosition() { return position; }
};
struct Context { Player player; crypt_ptr<Player> local() { return &player; } } context;
auto ctx = &context;
struct Globals { float curtime=123, frametime=.02f, intervalpertick=.015625f; } global_state;
auto globals = &global_state;
#define TICKS_TO_TIME(t) ((t) * globals->intervalpertick)
struct Exploits { bool charging=false; } exploit_state;
auto exploits = &exploit_state;
struct EnginePrediction {
    bool m_bInPrediction=false, m_bEnginePaused=false;
    void SetupMove(Player*, CUserCmd*, void*, CMoveData*) {}
    void FinishMove(Player*, CUserCmd*, CMoveData*) {}
} engine_state;
auto prediction = &engine_state;
struct Movement {
    int begins=0, ends=0;
    void StartTrackPredictionErrors(Player*) { ++begins; }
    void FinishTrackPredictionErrors(Player*) { ++ends; }
    void ProcessMovement(Player*, CMoveData*) {}
    void Reset() {}
} movement_state;
auto movement = &movement_state;
struct Helper { Player* host=nullptr; void set_host(Player* p) { host=p; } } helper;
crypt_ptr<Helper> movehelper = &helper;
struct Convar { float GetFloat() { return 450; } } convar;
enum { CONVAR_CL_FORWARDSPEED, CONVAR_CL_SIDESPEED, CONVAR_CL_UPSPEED };
struct Convars { Convar* convars[3]={&convar,&convar,&convar}; } convar_state;
auto convars_manager = &convar_state;
int seed=-1; Player* prediction_owner=nullptr;
int* seed_ptr=&seed; Player** owner_ptr=&prediction_owner;
enum { SIGNATURE_PREDICTION_RANDOM_SEED, SIGNATURE_PREDICTION_PLAYER };
struct Signatures { void* signatures[2]={&seed_ptr,&owner_ptr}; } signature_state;
auto signatures_manager = &signature_state;
unsigned MD5_PseudoRandom(int value) { return value + 100; }
class Prediction {
    float curtime=0, frametime=0;
    bool active=false;
    CUserCmd* active_command=nullptr;
    crypt_ptr<int> prediction_random_seed, prediction_player;
    bool in_prediction=false;
    CMoveData move_data;
    float velocity_modifier=1;
    Vector origin;
public:
    void start(crypt_ptr<CUserCmd>);
    void end();
};
"""

checks = r"""
int main() {
    Prediction p;
    CUserCmd outer, simulated;
    p.start(&outer);
    assert(seed == outer.random_seed && prediction_owner == &ctx->player);
    assert(helper.host == &ctx->player && prediction->m_bInPrediction);
    p.start(&simulated);
    p.start(&simulated);
    exploits->charging = true; // Recharge begins after prediction was opened.
    p.end();
    assert(globals->curtime == 123 && globals->frametime == .02f);
    assert(!prediction->m_bInPrediction && helper.host == nullptr);
    assert(ctx->player.current == nullptr && seed == -1 && prediction_owner == nullptr);
    assert(movement_state.begins == 1 && movement_state.ends == 1);
    p.end(); // Cleanup is idempotent.
    p.start(&outer); // Already charging: no prediction context opened.
    p.end();
    assert(movement_state.begins == 1 && movement_state.ends == 1);
    assert(globals->curtime == 123);
    exploits->charging = false;
    prediction->m_bInPrediction = true;
    p.start(&outer);
    p.end();
    assert(prediction->m_bInPrediction); // Preserve a pre-existing engine flag.
    assert(movement_state.begins == 2 && movement_state.ends == 2);
}
"""

with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "prediction_check.cpp"
    cpp.write_text(stub + start + end + checks)
    exe = directory / "prediction_check.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Prediction checks passed")
