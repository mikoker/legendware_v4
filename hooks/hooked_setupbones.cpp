// This is an independent project of an individual developer. Dear PVS-Studio, please check it.
// PVS-Studio Static Code Analyzer for C, C++, C#, and Java: http://www.viva64.com

#include "hooks.h"
#include "../features/bone_cache.h"

bool __fastcall hooked_setupbones(void* ecx, void* edx, matrix3x4_t* bone_world_out, int max_bones, int bone_mask, float current_time)
{
	// Historical scans only copy a frozen matrix; avoid convar callbacks on every ray.
	if (ecx)
	{
		auto player = crypt_ptr <Player> ((Player*)((uintptr_t)ecx - 0x4));
		if (player->valid())
		{
			const auto index = player->EntIndex();
			const auto frozen = index >= 1 && index <= 64 && historical_bone_cache[index].player == player.get() &&
				historical_bone_cache[index].spawn_time == player->m_flSpawnTime() && historical_bone_cache[index].model == player->GetModel();
			if (frozen)
			{
				const auto count = player->m_CachedBoneData().Count();
				const auto cache_valid = count > 0 && count <= MAXSTUDIOBONES && player->m_CachedBoneData().Base() &&
					bone_mask != -1 && (historical_bone_cache[index].mask & bone_mask) == bone_mask;
				if (!cache_valid || (bone_world_out && max_bones < count))
					return false;
				if (bone_world_out)
					memcpy(bone_world_out, player->m_CachedBoneData().Base(), count * sizeof(matrix3x4_t));
				return true;
			}
		}
	}

	auto result = false;
	auto r_jiggle_bones_backup = convars_manager->convars[CONVAR_R_JIGGLE_BONES]->GetInt();

	convars_manager->convars[CONVAR_R_JIGGLE_BONES]->SetValue(0);

	if (ecx)
	{
		auto player = crypt_ptr <Player> ((Player*)((uintptr_t)ecx - 0x4));

		if (player->valid())
		{
			auto animstate = player->get_animation_state();
			auto previous_weapon = animstate ? crypt_ptr <Weapon> (animstate->weapon_last_bone_setup) : crypt_ptr <Weapon>();

			if (previous_weapon)
				animstate->weapon_last_bone_setup = animstate->weapon;

			result = ((SetupBones)original_setupbones)(ecx, bone_world_out, max_bones, bone_mask, current_time);

			if (previous_weapon)
				animstate->weapon_last_bone_setup = previous_weapon.get();
		}
		else
			result = ((SetupBones)original_setupbones)(ecx, bone_world_out, max_bones, bone_mask, current_time);
	}
	else
		result = ((SetupBones)original_setupbones)(ecx, bone_world_out, max_bones, bone_mask, current_time);

	convars_manager->convars[CONVAR_R_JIGGLE_BONES]->SetValue(r_jiggle_bones_backup);
	return result;
}
