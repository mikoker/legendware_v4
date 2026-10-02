"""Check the production probability threshold and damage filtering over 256 seeds."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "features/aim.cpp").read_text()
method = source[source.index("bool Aim::is_hit_chanced("):source.index("float Aim::get_hit_chance(")]
cpp = r"""
#include <cassert>
#include <cmath>
#include <algorithm>
#include <limits>
using std::clamp;
template<class T> struct crypt_ptr { T* p;crypt_ptr(T* v=nullptr):p(v) {} T* get() const { return p; } T* operator->() const { return p; } };
struct Vector { float x=0,y=0,z=0; Vector operator+(Vector) const { return {}; } Vector operator*(float) const { return {}; } Vector Normalized() const { return {}; } };
struct Player {};
struct AnimationData {};
namespace math { void angle_vectors(const Vector&,Vector*,Vector*,Vector*) {} }
enum { CONVAR_WEAPON_ACCURACY_NOSPREAD=0 };
struct Convar { bool enabled=false;bool GetBool() { return enabled; } } cv;
struct Convars { Convar* convars[1]{&cv}; } cvs;auto convars_manager=&cvs;
struct WeaponData { float range=1000; } weapon;
struct Context { Vector shoot_position; WeaponData* weapon_data() { return &weapon; } } context;auto ctx=&context;
struct Config { struct { bool automatic_wall=true; } rage; } configuration;auto config=&configuration;
int sample=0,geometric_hits=0,damage_hits=0;
struct Penetration { struct Result { int damage; }; Result run(Vector,Vector,crypt_ptr<Player>,bool) { return {sample<damage_hits?100:0}; } } penetration_instance;auto penetration=&penetration_instance;
struct Aim {
    Vector get_spread(int i) { sample=i;return {}; }
    bool hitbox_intersection(int,int,crypt_ptr<Player>,crypt_ptr<AnimationData>,Vector) { return sample<geometric_hits; }
    bool is_hit_chanced(float,const Vector&,int,int,crypt_ptr<Player>,crypt_ptr<AnimationData>,bool,int);
};
""" + method + r"""
int main() {
    Aim aim;Player player;AnimationData record;
    auto check=[&](float chance,bool damage=false) { return aim.is_hit_chanced(chance,{},0,0,&player,&record,damage,50); };
    geometric_hits=253;
    assert(!check(99)); // 253/256 is only 98.828125%.
    geometric_hits=254;assert(check(99));
    geometric_hits=255;assert(!check(100));
    geometric_hits=256;assert(check(100));
    geometric_hits=127;assert(!check(50));
    geometric_hits=128;assert(check(50));
    geometric_hits=0;assert(check(0));assert(!check(0.01f));
    assert(check(-10));assert(!check(110));
    assert(!check(std::numeric_limits<float>::quiet_NaN()));
    assert(!check(std::numeric_limits<float>::infinity()));
    geometric_hits=256;damage_hits=127;assert(!check(50,true));
    damage_hits=128;assert(check(50,true));
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    path = directory / "hitchance.cpp"
    path.write_text(cpp)
    exe = directory / "hitchance.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(path), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("Hitchance checks passed")
