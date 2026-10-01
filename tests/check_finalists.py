"""Exercise the production finalist retention rule. Run in an x86 VS shell."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/aim.cpp").read_text()
rule = source[source.index("void Aim::consider_finalist("):source.index("void Aim::scan_hitboxes(")]
cpp = r"""
#include <cassert>
#include <vector>
enum { HITBOX_HEAD, HITBOX_NECK, HITBOX_PELVIS, HITBOX_STOMACH, HITBOX_LOWER_CHEST, HITBOX_CHEST, HITBOX_UPPER_CHEST };
template<class T> struct Ptr { T* p=nullptr; T* get() const { return p; } };
struct Target {
    int damage=0, hitbox=HITBOX_HEAD;
    Ptr<int> player, data;
    struct { bool prefer_safe=false; } hitbox_s;
    struct { bool safe=false; } point;
};
class Aim {
public:
    std::vector<Target> finalists;
    void consider_finalist(Target&);
};
""" + rule + r"""
int main() {
    Aim aim;
    int player=1, record=1;
    Target head;
    head.player.p=&player; head.data.p=&record; head.damage=140;
    Target body=head;
    body.hitbox=HITBOX_STOMACH; body.damage=80;
    aim.consider_finalist(head);
    aim.consider_finalist(body);
    // A high-damage head through a slit must not discard the body fallback.
    assert(aim.finalists.size() == 2);
    assert(aim.finalists[0].damage == 140 && aim.finalists[1].damage == 80);
    body.damage=90;
    aim.consider_finalist(body);
    assert(aim.finalists.size() == 2 && aim.finalists[1].damage == 90);
    body.hitbox_s.prefer_safe=true;
    body.point.safe=true;
    body.damage=85;
    aim.consider_finalist(body);
    assert(aim.finalists[1].point.safe && aim.finalists[1].damage == 85);
    body.point.safe=false; body.damage=100;
    aim.consider_finalist(body);
    assert(aim.finalists[1].point.safe && aim.finalists[1].damage == 85);
    int other=2;
    body.player.p=&other;
    aim.consider_finalist(body);
    assert(aim.finalists.size() == 3);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    path = directory / "finalists.cpp"
    path.write_text(cpp)
    exe = directory / "finalists.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(path), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Finalist checks passed")
