"""Run the real impact matcher and event-settlement rule without the game.

Run from an x86 Visual Studio developer shell: python tests/check_shots.py
"""
import pathlib
import subprocess
import tempfile


root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/aim.cpp").read_text()
matcher = source[source.index("crypt_ptr<Shot> Aim::find_impact_shot("):source.index("void Aim::commit_shot(")]
header = (root / "features/aim.h").read_text()
begin = header.index("bool events_settled(")
settled = header[begin:header.index("\n\t}", begin) + len("\n\t}")]
begin = header.index("bool matches_weapon(")
weapon_match = header[begin:header.index("\n\t}", begin) + len("\n\t}")]

stub = r"""
#include <cassert>
#include <vector>
#include <string>
template<class T> struct crypt_ptr {
    T* p=nullptr;
    crypt_ptr(T* value=nullptr): p(value) {}
    T* get() const { return p; }
    T* operator->() const { return p; }
    explicit operator bool() const { return p != nullptr; }
};
struct Shot {
    bool start=false, end=false, hurt=false, impacts=false, ambiguous=false;
    unsigned int fire_sequence=0;
    int event_tickcount=0, last_event_tickcount=0, impact_count=0;
    std::string weapon_name;
""" + settled + weapon_match + r"""
};
std::vector<Shot> shots;
class Aim { public: crypt_ptr<Shot> find_impact_shot(unsigned int); };
"""

checks = r"""
int main() {
    Aim aim;
    shots.resize(2);
    shots[0].start=true;
    shots[0].fire_sequence=1;
    shots[0].event_tickcount=100;
    shots[0].last_event_tickcount=100;
    // A queued next command must not steal additional wallbang impacts.
    for (int i=0; i<4; ++i) {
        auto shot=aim.find_impact_shot(1);
        assert(shot.get() == &shots[0]);
        ++shot->impact_count;
        shot->impacts=true;
    }
    assert(shots[0].impact_count == 4 && shots[1].impact_count == 0);
    assert(!shots[0].events_settled(102));
    shots[0].last_event_tickcount=102; // A later hurt/impact resets the quiet window.
    assert(!shots[0].events_settled(103));
    assert(shots[0].events_settled(105));
    shots[1].start=true;
    shots[1].fire_sequence=2;
    shots[1].event_tickcount=110;
    assert(aim.find_impact_shot(2).get() == &shots[1]);
    assert(!shots[0].ambiguous && !shots[1].ambiguous);
    // An untracked manual weapon_fire must not attach impacts to an old shot.
    assert(!aim.find_impact_shot(3));
    shots[1].event_tickcount=100;
    aim.find_impact_shot(2);
    assert(shots[0].ambiguous && shots[1].ambiguous);
    shots[1].end=true;
    assert(!aim.find_impact_shot(2));
    Shot pending;
    assert(!pending.events_settled(10000));
    pending.weapon_name="scar20";
    assert(pending.matches_weapon("scar20"));
    assert(!pending.matches_weapon("inferno"));
    assert(!pending.matches_weapon("hegrenade"));
    assert(!pending.matches_weapon("knife"));
    assert(!pending.matches_weapon("ssg08"));
    assert(!pending.matches_weapon(nullptr));
}
"""

with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "shot_check.cpp"
    cpp.write_text(stub + matcher + checks)
    exe = directory / "shot_check.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Shot checks passed")
