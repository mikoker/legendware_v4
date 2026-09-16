// This is an independent project of an individual developer. Dear PVS-Studio, please check it.
// PVS-Studio Static Code Analyzer for C, C++, C#, and Java: http://www.viva64.com

#include "hooks.h"
#include "..\features\features.h"
#include "..\features\animations.h"
#include "..\features\chams.h"

void __fastcall hooked_drawmodelexecute(IVModelRender* ecx, void* edx, IMatRenderContext* context, const DrawModelState_t& state, const ModelRenderInfo_t& info, matrix3x4_t* bone_world)
{
	static auto original = hooks_manager->hooks[HOOK_MODELRENDER]->get_func_address <DrawModelExecute> (crypt_hash_n(21));

	if (!engine->IsInGame() || !ctx->local()->valid())
		return original(ecx, context, state, info, bone_world);

	auto model_name = info.pModel ? modelinfo->GetModelName(info.pModel) : nullptr;
	auto is_arms = model_name && strstr(model_name, crypt_str("arms"));
	auto is_sleeve = model_name && strstr(model_name, crypt_str("sleeve"));
	auto is_hands = is_arms || is_sleeve;
	auto is_viewmodel_weapon = model_name && strstr(model_name, crypt_str("weapons/v_")) && !is_hands;

	// Do not disturb material overrides owned by the engine's nested render passes.
	if (modelrender->IsForcedMaterialOverride() && !is_hands && !is_viewmodel_weapon)
		return original(ecx, context, state, info, bone_world);

	if (is_hands || is_viewmodel_weapon)
	{
		auto& cfg = config->visuals.player_type[LOCAL];
		auto called_original = false;

		if (is_hands)
		{
			if (cfg.chams_hand)
			{
				chams->MaterialOverride(cfg.chams_hand_type, cfg.chams_hand_clr);
				original(ecx, context, state, info, bone_world);
				chams->MaterialReset();

				if (cfg.chams_hand_modifiers && cfg.chams_hand_modifiers_arr.size() >= 3)
				{
					for (auto i = 0; i < 3; ++i)
					{
						if (!cfg.chams_hand_modifiers_arr[i])
							continue;

						chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_hand_modifiers_clr[i]);
						original(ecx, context, state, info, bone_world);
						chams->MaterialReset();
					}
				}

				called_original = true;
			}
		}
		else // viewmodel weapon
		{
			if (cfg.chams_weapon)
			{
				chams->MaterialOverride(cfg.chams_weapon_type, cfg.chams_weapon_clr);
				original(ecx, context, state, info, bone_world);
				chams->MaterialReset();

				if (cfg.chams_weapon_modifiers && cfg.chams_weapon_modifiers_arr.size() >= 3)
				{
					for (auto i = 0; i < 3; ++i)
					{
						if (!cfg.chams_weapon_modifiers_arr[i])
							continue;

						chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_weapon_modifiers_clr[i]);
						original(ecx, context, state, info, bone_world);
						chams->MaterialReset();
					}
				}

				called_original = true;
			}
		}

		if (!called_original)
			return original(ecx, context, state, info, bone_world);

		return;
	}

	auto entity = crypt_ptr <Entity> ((Entity*)entitylist->GetClientEntity(info.entity_index));

	if (!entity)
		return original(ecx, context, state, info, bone_world);

	auto class_id = entity->get_class_id();

	// world weapons
	if (class_id == CAK47 || class_id == CDEagle || class_id == CBaseGrenade || class_id == CC4 ||
		class_id == CSensorGrenade || class_id == CSmokeGrenade || class_id == CDecoyGrenade ||
		class_id == CHEGrenade || class_id == CIncendiaryGrenade || class_id == CMolotovGrenade ||
		class_id == CFlashbang || class_id >= CWeaponAug && class_id <= CWeaponZoneRepulsor)
	{
		auto index = WEAPON;

		if (class_id == CC4)
			index = C4;
		else if (class_id == CBaseGrenade || class_id == CSensorGrenade || class_id == CSmokeGrenade ||
			class_id == CDecoyGrenade || class_id == CHEGrenade || class_id == CIncendiaryGrenade ||
			class_id == CMolotovGrenade || class_id == CFlashbang)
			index = NADE;

		auto& cfg = config->visuals.world.weapon_type[index];

		if (cfg.chams)
		{
			chams->MaterialOverride(cfg.chams_type, cfg.chams_clr);
			original(ecx, context, state, info, bone_world);
			chams->MaterialReset();

			if (cfg.chams_modifer && cfg.chams_modifiers_arr.size() >= 3)
			{
				for (auto i = 0; i < 3; ++i)
				{
					if (!cfg.chams_modifiers_arr[i])
						continue;

					chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_modifiers_clr[i]);
					original(ecx, context, state, info, bone_world);
					chams->MaterialReset();
				}
			}
		}

		return original(ecx, context, state, info, bone_world);
	}
	// planted c4
	else if (class_id == CPlantedC4)
	{
		auto& cfg = config->visuals.world.weapon_type[C4];

		if (cfg.chams)
		{
			chams->MaterialOverride(cfg.chams_type, cfg.chams_clr);
			original(ecx, context, state, info, bone_world);
			chams->MaterialReset();

			if (cfg.chams_modifer && cfg.chams_modifiers_arr.size() >= 3)
			{
				for (auto i = 0; i < 3; ++i)
				{
					if (!cfg.chams_modifiers_arr[i])
						continue;

					chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_modifiers_clr[i]);
					original(ecx, context, state, info, bone_world);
					chams->MaterialReset();
				}
			}
		}

		return original(ecx, context, state, info, bone_world);
	}
	// ragdolls
	else if (class_id == CCSRagdoll)
	{
		auto type = ENEMY;

		if (entity->m_iTeamNum() == ctx->local()->m_iTeamNum() && !ctx->friendly_fire)
			type = TEAM;

		auto& cfg = config->visuals.player_type[type];

		if (cfg.chams_enable && cfg.chams_ragdoll)
		{
			chams->MaterialOverride(cfg.chams_type_visible, cfg.chams_clr_visible);
			original(ecx, context, state, info, bone_world);
			chams->MaterialReset();

			if (cfg.chams_modifiers_visible && cfg.chams_modifiers_arr_visible.size() >= 3)
			{
				for (auto i = 0; i < 3; ++i)
				{
					if (!cfg.chams_modifiers_arr_visible[i])
						continue;

					chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_modifiers_clr_visible[i]);
					original(ecx, context, state, info, bone_world);
					chams->MaterialReset();
				}
			}
		}

		return original(ecx, context, state, info, bone_world);
	}

	if (class_id != CCSPlayer)
		return original(ecx, context, state, info, bone_world);

	auto player = crypt_ptr <Player> ((Player*)entity.get());

	if (!player->valid())
		return original(ecx, context, state, info, bone_world);

	auto type = LOCAL;

	if (player.get() != ctx->local().get())
	{
		if (player->m_iTeamNum() != ctx->local()->m_iTeamNum() || ctx->friendly_fire)
			type = ENEMY;
		else
			type = TEAM;
	}

	auto& cfg = config->visuals.player_type[type];

	if (!cfg.chams_enable)
		return original(ecx, context, state, info, bone_world);

	auto alpha_modifier = 1.0f;

	if (type == LOCAL && cfg.transparency_in_scope && ctx->local()->m_bIsScoped())
		alpha_modifier = 1.0f - (float)cfg.transparency_in_scope / 100.0f;

	// Invisible chams must be drawn before the normal model, otherwise they tint
	// the visible model instead of remaining an occluded-only pass.
	if (cfg.chams_invisible)
	{
		chams->MaterialOverride(cfg.chams_type_invisible, cfg.chams_clr_invisible, true);
		original(ecx, context, state, info, bone_world);
		chams->MaterialReset();

		if (cfg.chams_modifiers_invisible && cfg.chams_modifiers_arr_invisible.size() >= 3)
		{
			for (auto i = 0; i < 3; ++i)
			{
				if (!cfg.chams_modifiers_arr_invisible[i])
					continue;

				chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_modifiers_clr_invisible[i], true);
				original(ecx, context, state, info, bone_world);
				chams->MaterialReset();
			}
		}
	}

	// The normal pass only contributes when it covers ignore-z chams or remains
	// visible through a translucent/disabled visible pass.
	if (cfg.chams_invisible || !cfg.chams_visible || cfg.chams_clr_visible[3] * alpha_modifier < 1.0f)
		original(ecx, context, state, info, bone_world);

	// backtrack (ghost) chams
	if (cfg.chams_ghost)
	{
		for (auto& record : animations->animation_data[info.entity_index])
		{
			if (record.invalid || record.dormant || record.simulation_time == player->m_flSimulationTime())
				continue;

			chams->MaterialOverride(cfg.chams_ghost_type, cfg.chams_ghost_clr);
			original(ecx, context, state, info, record.matrix[MATRIX_VISUAL]);
			chams->MaterialReset();

			if (cfg.chams_ghost_modifiers && cfg.chams_ghost_modifiers_arr.size() >= 3)
			{
				for (auto i = 0; i < 3; ++i)
				{
					if (!cfg.chams_ghost_modifiers_arr[i])
						continue;

					chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_ghost_modifiers_clr[i]);
					original(ecx, context, state, info, record.matrix[MATRIX_VISUAL]);
					chams->MaterialReset();
				}
			}

			// The deque holds up to 64 history records; one latest valid record is
			// sufficient for the ghost effect and avoids multiplying model draws.
			break;
		}
	}

	// fake chams (local desync pose)
	if (type == LOCAL && cfg.chams_fake)
	{
		chams->MaterialOverride(cfg.chams_fake_type, cfg.chams_fake_clr);
		original(ecx, context, state, info, ctx->fake);
		chams->MaterialReset();

		if (cfg.chams_fake_modifiers && cfg.chams_fake_modifiers_arr.size() >= 3)
		{
			for (auto i = 0; i < 3; ++i)
			{
				if (!cfg.chams_fake_modifiers_arr[i])
					continue;

				chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_fake_modifiers_clr[i]);
				original(ecx, context, state, info, ctx->fake);
				chams->MaterialReset();
			}
		}
	}

	// on shot chams
	if (cfg.chams_shot && !animations->animation_data[info.entity_index].empty() && animations->animation_data[info.entity_index].front().shot)
	{
		chams->MaterialOverride(cfg.chams_shot_type, cfg.chams_shot_clr);
		original(ecx, context, state, info, bone_world);
		chams->MaterialReset();

		if (cfg.chams_shot_modifiers && cfg.chams_shot_modifiers_arr.size() >= 3)
		{
			for (auto i = 0; i < 3; ++i)
			{
				if (!cfg.chams_shot_modifiers_arr[i])
					continue;

				chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_shot_modifiers_clr[i]);
				original(ecx, context, state, info, bone_world);
				chams->MaterialReset();
			}
		}
	}

	// visible chams (drawn last so they stay on top of the normal model)
	if (cfg.chams_visible)
	{
		chams->MaterialOverride(cfg.chams_type_visible, cfg.chams_clr_visible, false, false, alpha_modifier);
		original(ecx, context, state, info, bone_world);
		chams->MaterialReset();

		if (cfg.chams_modifiers_visible && cfg.chams_modifiers_arr_visible.size() >= 3)
		{
			for (auto i = 0; i < 3; ++i)
			{
				if (!cfg.chams_modifiers_arr_visible[i])
					continue;

				chams->MaterialOverride(MATERIAL_GLASS + i, cfg.chams_modifiers_clr_visible[i], false, false, alpha_modifier);
				original(ecx, context, state, info, bone_world);
				chams->MaterialReset();
			}
		}
	}

	// do not call original() again: the cham passes above already rendered the model
}
