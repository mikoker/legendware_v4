"""Check real VMT initialization and hashed slot bounds with x86 cl."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
header = (root / "hooks/vfunc_hook.hpp").read_text().replace('#include "..\\includes.h"', '')
source = (root / "hooks/vfunc_hook.cpp").read_text().replace('#include "vfunc_hook.hpp"', '')
stub = r"""
#include <cassert>
#include <cstdint>
#include <cstring>
using DWORD=unsigned long;
using PDWORD=DWORD*;
using FARPROC=void(*)();
constexpr DWORD PAGE_EXECUTE_READWRITE=0x40;
bool VirtualProtect(void*,unsigned long,DWORD,DWORD* old){*old=0x20; return true;}
#define IS_INTRESOURCE(value) ((uintptr_t)(value)<65536)
unsigned crypt_hash_rn(unsigned index){return index^0x12345678;}
template<class T> struct crypt_ptr {
    T* p=nullptr;
    crypt_ptr(T* value=nullptr):p(value){}
    T* get(){return p;}
    explicit operator bool(){return p!=nullptr;}
};
"""
checks = r"""
int main(){
    vmthook empty;
    assert(!empty.get_func_address<void(*)()>(crypt_hash_rn(0)));
    assert(!empty.hook_function(0x40000,crypt_hash_rn(0)));
    assert(!empty.initialize(nullptr));
    PDWORD missing=nullptr;
    assert(!empty.initialize(&missing));
    DWORD table[]={0x11111,0x20000,0x30000,0}; // RTTI then two slots.
    PDWORD object=&table[1];
    vmthook hook(&object);
    assert(object[-1]==0x11111);
    assert(hook.get_func_address<void(*)()>(crypt_hash_rn(1))==(void(*)())0x30000);
    assert(hook.hook_function(0x40000,crypt_hash_rn(1))==0x30000);
    assert(object[1]==0x40000);
    assert(!hook.hook_function(0x50000,crypt_hash_rn(2)));
    assert(!hook.get_func_address<void(*)()>(crypt_hash_rn(2)));
    assert(!hook.hook_function(0x50000,0xffffffff));
    assert(!hook.get_func_address<void(*)()>(0xffffffff));
    assert(object[0]==0x20000 && object[1]==0x40000);
    hook.unhook();
    assert(object==&table[1] && object[1]==0x30000);
}
"""
with tempfile.TemporaryDirectory() as tmp:
    directory = pathlib.Path(tmp)
    cpp = directory / "vfunc_bounds.cpp"
    cpp.write_text(stub + header + source + checks)
    exe = directory / "vfunc_bounds.exe"
    subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", str(cpp), f"/Fe:{exe}"], cwd=directory, check=True)
    subprocess.run([str(exe)], check=True)
print("VMT bounds checks passed")
