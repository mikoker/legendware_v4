"""Exercise production dormant measurement acceptance and zero flags in x86 VS."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/dormant.cpp").read_text()
methods = source[source.index("bool Dormant_esp::setup_adjust("):source.index("bool Dormant_esp::valid_sound(")]
header = (root / "features/dormant.h").read_text().replace('#include "../globals.h"', '')
cpp = r"""
#include <cassert>
#include <cmath>
#include <vector>
using std::abs;
template<class T> struct crypt_ptr {
    T* p; crypt_ptr(T* v=nullptr):p(v) {}
    T* get() const { return p; } T* operator->() const { return p; }
    explicit operator bool() const { return p != nullptr; }
};
struct Vector {
    float x=0, y=0, z=0;
    Vector(float a=0,float b=0,float c=0):x(a),y(b),z(c) {}
    Vector operator+(const Vector& o) const { return {x+o.x,y+o.y,z+o.z}; }
    Vector operator-(const Vector& o) const { return {x-o.x,y-o.y,z-o.z}; }
    void Zero() { x=y=z=0; }
};
enum { FL_ONGROUND=1, FL_DUCKING=2, MASK_PLAYERSOLID=3 };
struct Player {
    int index=1, flags=0; Vector origin;
    int EntIndex() { return index; } int& m_fFlags() { return flags; }
    void set_abs_origin(Vector v) { origin=v; }
};
struct SndInfo_t { int m_nSoundSource=1; Vector* m_pOrigin=nullptr; };
struct CGameTrace { bool allsolid=false,startsolid=false; float fraction=1; Vector endpos; };
struct Ray_t { void Init(Vector,Vector) {} };
struct CTraceFilter { void* pSkip=nullptr; };
struct Trace { CGameTrace result; void TraceRay(Ray_t&,int,CTraceFilter*,CGameTrace* out) { *out=result; } } trace_instance;
auto enginetrace=&trace_instance;
struct Globals { float realtime=20; } globals_instance;
auto globals=&globals_instance;
struct Esp { Vector dormant_origin[65]; } esp_instance;
auto esp=&esp_instance;
template<class T> struct CUtlVector { void RemoveAll() {} };
""" + header + methods + r"""
void Dormant_esp::start() {}
bool Dormant_esp::valid_sound(SndInfo_t&) { return true; }
int main() {
    Dormant_esp dormant;
    Player player; player.flags=FL_ONGROUND|FL_DUCKING;
    // An uninitialized entry is invalid even near time zero.
    globals->realtime=0;
    assert(!dormant.adjust_sound(&player));
    globals->realtime=20;
    Vector sound_origin(10,20,30);
    SndInfo_t sound; sound.m_pOrigin=&sound_origin;
    // Airborne measurement must publish flags == 0, not preserve grounded.
    assert(dormant.setup_adjust(&player,sound));
    dormant.m_cSoundPlayers[1].Override(sound);
    assert(dormant.adjust_sound(&player));
    assert(player.flags==0 && player.origin.x==10);
    // A rejected measurement cannot refresh or corrupt an older valid entry.
    globals->realtime=21;
    trace_instance.result.allsolid=true;
    trace_instance.result.fraction=0;
    trace_instance.result.endpos=Vector(999,999,999);
    assert(!dormant.setup_adjust(&player,sound));
    assert(dormant.m_cSoundPlayers[1].m_iReceiveTime==20 && sound_origin.x==10);
    trace_instance.result.allsolid=false;
    trace_instance.result.startsolid=true;
    assert(!dormant.setup_adjust(&player,sound));
    // Position-only observer data must not override authoritative player flags.
    dormant.m_cSoundPlayers[1].flags_valid=false;
    player.flags=FL_ONGROUND;
    assert(dormant.adjust_sound(&player) && player.flags==FL_ONGROUND);
    globals->realtime=31;
    assert(!dormant.adjust_sound(&player));
    dormant.m_cSoundPlayers[1].reset(true,Vector(1,2,3),0);
    assert(dormant.adjust_sound(&player) && player.flags==0);
    dormant.reset();
    assert(!dormant.adjust_sound(&player));
    player.index=65;
    assert(!dormant.adjust_sound(&player));
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    path = directory / "dormant.cpp"
    path.write_text(cpp)
    exe = directory / "dormant.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(path), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Dormant checks passed")
