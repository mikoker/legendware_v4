"""Run the real impact matcher and event-settlement rule without the game.

Run from an x86 Visual Studio developer shell: python tests/check_shots.py
"""
import pathlib
import subprocess
import tempfile


root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/aim.cpp").read_text()
matcher = source[source.index("crypt_ptr<Shot> Aim::find_fire_shot("):source.index("void Aim::commit_shot(")]
header = (root / "features/aim.h").read_text()
begin = header.index("bool events_settled(")
settled = header[begin:header.index("\n\t}", begin) + len("\n\t}")]
begin = header.index("bool matches_weapon(")
weapon_match = header[begin:header.index("\n\t}", begin) + len("\n\t}")]
begin = header.index("bool accepts_event(")
accepts_event = header[begin:header.index("\n\t}", begin) + len("\n\t}")]
begin = header.index("int event_clock(")
event_clock = header[begin:header.index("\n\t}", begin) + len("\n\t}")]
send_method = source[source.index("void Aim::mark_shots_sent("):source.index("crypt_ptr<Shot> Aim::find_fire_shot(")]
events = (root / "hooks/hooked_events.cpp").read_text()
begin = events.index("\t\t\t\tcurrent_shot->start = true;")
fire_publish = events[begin:events.index("\n\t\t\t}", begin)].replace("globals->tickcount", "tick")
begin = events.index("\t\t\t\t\tcurrent_shot->hurt = true;")
end = events.index("current_shot->state = SHOT_HURT;", begin) + len("current_shot->state = SHOT_HURT;")
hurt_publish = events[begin:end].replace("globals->tickcount", "tick")

stub = r"""
#include <cassert>
#include <vector>
#include <string>
#include <cstring>
enum {SHOT_CREATED,SHOT_SENT,SHOT_FIRED,SHOT_COLLECTING_IMPACTS,SHOT_HURT};
template<class T> struct crypt_ptr {
    T* p=nullptr;
    crypt_ptr(T* value=nullptr): p(value) {}
    T* get() const { return p; }
    T* operator->() const { return p; }
    explicit operator bool() const { return p != nullptr; }
};
struct Shot {
    bool start=false, end=false, hurt=false, impacts=false, ambiguous=false;
    bool outgoing=false,latency=false;
    int state=SHOT_CREATED,index=0,expected_bullets=1,packet_command_number=0,tickcount=0;
    int sent_tickcount=-1;
    unsigned int fire_sequence=0;
    int event_tickcount=0, last_event_tickcount=0, impact_count=0;
    std::string weapon_name;
""" + settled + weapon_match + accepts_event + event_clock + r"""
};
std::vector<Shot> shots;
struct CUserCmd {int command_number=0;};
bool sending=true;
struct Context {crypt_ptr<bool> send_packet=&sending;} context;
auto ctx=&context;
struct Globals {int tickcount=116;} globals_state;
auto globals=&globals_state;
class Aim { public:
    void mark_shots_sent(crypt_ptr<CUserCmd>);
    crypt_ptr<Shot> find_impact_shot(unsigned int);
    crypt_ptr<Shot> find_fire_shot(const char*,int,int);
    crypt_ptr<Shot> find_hurt_shot(int,const char*,int,int,unsigned int);
};
void publish_fire(crypt_ptr<Shot> current_shot,int tick,unsigned int latest_fire_sequence){
""" + fire_publish + r"""
}
void publish_hurt(crypt_ptr<Shot> current_shot,int tick){
""" + hurt_publish + r"""
}
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
    assert(pending.matches_weapon("weapon_scar20"));
    pending.weapon_name="weapon_ssg08";
    assert(pending.matches_weapon("ssg08") && pending.matches_weapon("weapon_ssg08"));
    assert(!pending.matches_weapon("weapon_"));
    shots.clear(); shots.resize(1);
    auto& tracked=shots[0];
    tracked.outgoing=true; tracked.state=SHOT_SENT; tracked.tickcount=200;
    tracked.index=5; tracked.weapon_name="ssg08";
    auto fire=aim.find_fire_shot("weapon_ssg08",202,16);
    assert(fire.get()==&tracked);
    publish_fire(fire,202,3);
    assert(aim.find_impact_shot(3).get()==&tracked);
    auto hurt=aim.find_hurt_shot(5,"ssg08",202,16,3);
    assert(hurt.get()==&tracked); // A confirmed hurt needs no preceding impact.
    publish_hurt(hurt,202);
    assert(tracked.hurt && !tracked.latency && tracked.state==SHOT_HURT);
    // Some event orders deliver hurt before weapon_fire.
    tracked=Shot{}; tracked.outgoing=true; tracked.state=SHOT_SENT;
    tracked.tickcount=300; tracked.index=5; tracked.weapon_name="ssg08";
    hurt=aim.find_hurt_shot(5,"weapon_ssg08",302,16,3);
    assert(hurt.get()==&tracked && tracked.ambiguous);
    tracked.latency=true;
    publish_hurt(hurt,302);
    fire=aim.find_fire_shot("weapon_ssg08",302,16);
    assert(fire.get()==&tracked);
    publish_fire(fire,302,4);
    assert(tracked.hurt && tracked.state==SHOT_HURT && !tracked.latency);
    assert(aim.find_impact_shot(4).get()==&tracked);
    assert(!aim.find_hurt_shot(5,"ssg08",303,16,4)); // Single bullet not matched twice.
    tracked=Shot{}; tracked.outgoing=true; tracked.state=SHOT_SENT;
    tracked.tickcount=400; tracked.index=5; tracked.weapon_name="ssg08";
    assert(!aim.find_fire_shot("ssg08",500,16));
    assert(!aim.find_hurt_shot(5,"ssg08",399,16,5));
    assert(!aim.find_hurt_shot(6,"ssg08",402,16,5));
    assert(!aim.find_hurt_shot(5,"knife",402,16,5));
    tracked.outgoing=false;
    assert(!aim.find_hurt_shot(5,"ssg08",402,16,5));
    assert(!aim.find_fire_shot("ssg08",402,16));
    // A choked command's event window starts when its packet is actually sent.
    tracked.tickcount=100; globals->tickcount=116;
    CUserCmd packet; packet.command_number=116;
    aim.mark_shots_sent(&packet);
    assert(tracked.outgoing && tracked.sent_tickcount==116 && tracked.event_clock()==116);
    assert(aim.find_fire_shot("weapon_ssg08",130,16).get()==&tracked);
    assert(!tracked.accepts_event(133,16));
}
"""

with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "shot_check.cpp"
    cpp.write_text(stub + send_method + matcher + checks)
    exe = directory / "shot_check.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Shot checks passed")
