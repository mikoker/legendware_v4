#pragma once

#include "..\includes.h"
#include "..\data.h"
#include "..\globals.h"
#include "features.h"
#include "prediction.h"
#include "logs.h"
#include "resolver.h"
#include "bone_cache.h"

enum ROTATE_MODE
{
	MATRIX_VISUAL,
	MATRIX_VISUAL_INTERPOLATED,
	MATRIX_MAIN,
	MATRIX_ZERO,
	MATRIX_FIRST,
	MATRIX_FIRST_LOW,
	MATRIX_SECOND,
	MATRIX_SECOND_LOW,
	MATRIX_BASELINE,
	MATRIX_MAX
};

enum
{
	LAYERS_ORIGINAL,
	LAYERS_BASELINE,
	LAYERS_ZERO,
	LAYERS_FIRST,
	LAYERS_SECOND,
	LAYERS_MAX
};

struct NetworkAnimationSnapshot
{
	bool valid = false;
	int flags = 0;
	float simulation_time = 0.0f;
	float old_simulation_time = 0.0f;
	float duck_amount = 0.0f;
	float lower_body_yaw = 0.0f;
	Vector angles;
	Vector abs_angles;
	Vector velocity;
	Vector origin;
};

class AnimationData
{
public:
	int i;

	matrix3x4_t matrix[MATRIX_MAX][MAXSTUDIOBONES];
	unsigned int matrix_ready = 0;
	int matrix_mask[MATRIX_MAX] = {};
	AnimationLayer layers[LAYERS_MAX][13];
	ShortAnimationLayer server_layers[13];

	bool invalid;
	bool immune;
	bool dormant;
	bool shot;
	bool backup;
	bool exploit;
	bool extrapolated;
	bool strafing;
	bool walking;

	int choke;
	int server_tick;
	int flags;
	int bone_count;
	int resolver_type;
	int resolver_side;
	int velocity_state;
	int m_last_storred_tick;
	int creation_tick = 0;
	int simulation_tick_deviation = 0;
	bool simulation_regressed = false;
	ResolverResult resolver;
	NetworkAnimationSnapshot network;

	float curtime;
	float simulation_time;
	float old_simulation_time;
	float shot_time;
	float duck_amount;
	float lower_body_yaw_target;
	float max_speed;
	float roll;
	float collision_change_time = 0.0f;
	float collision_change_origin = 0.0f;
	uint32_t recent_bone_counter = 0;
	int readable_bones = 0;
	int writable_bones = 0;
	float last_bone_setup_time = 0.0f;
	HistoricalBoneCache previous_bone_cache;

	Vector angles;
	Vector abs_angles;
	Vector velocity;
	Vector origin;
	Vector render_origin;
	Vector mins;
	Vector maxs;

	AnimationState animation_state;

	AnimationData(int i = -1) //-V730
	{
		this->i = i;

		invalid = false;
		immune = false;
		dormant = false;
		backup = false;
		shot = false;
		exploit = false;
		extrapolated = false;
		strafing = false;
		walking = false;

		choke = 0;
		server_tick = 0;
		flags = 0;
		bone_count = 0;
		resolver_type = RESOLVER_NONE;
		resolver_side = MATRIX_MAIN;
		velocity_state = 0;
		m_last_storred_tick = 0;

		curtime = 0.0f;
		simulation_time = 0.0f;
		shot_time = 0.0f;
		old_simulation_time = 0.0f;
		duck_amount = 0.0f;
		lower_body_yaw_target = 0.0f;
		max_speed = 0.0f;
		roll = 0.0f;

		angles.Zero();
		abs_angles.Zero();
		velocity.Zero();
		origin.Zero();
		render_origin.Zero();
		mins.Zero();
		maxs.Zero();
	}

	AnimationData(crypt_ptr <Player> player) : AnimationData(player->EntIndex())
	{
		shot = false;
		backup = false;
		exploit = false;
		extrapolated = false;

		choke = 0;
		server_tick = 0;
		resolver_type = RESOLVER_NONE;
		resolver_side = MATRIX_MAIN;
		velocity_state = 0;
		m_last_storred_tick = 0;

		shot_time = 0.0f;
		max_speed = 0.0f;
		roll = 0.0f;

		store(player); //-V1053
	}

	virtual void store(crypt_ptr <Player> player, bool store_extra = true)
	{
		i = player->EntIndex();

		if (store_extra)
		{
			const auto count = player->m_CachedBoneData().Count();
			matrix_ready = 0;
			if (count > 0 && count <= MAXSTUDIOBONES && player->m_CachedBoneData().Base())
			{
				memcpy(matrix[MATRIX_MAIN], player->m_CachedBoneData().Base(), count * sizeof(matrix3x4_t));
				matrix_ready = 1u << MATRIX_MAIN;
			}
			matrix_mask[MATRIX_MAIN] = player->m_BoneAccessor().m_ReadableBones;
			readable_bones = player->m_BoneAccessor().m_ReadableBones;
			writable_bones = player->m_BoneAccessor().m_WritableBones;
			last_bone_setup_time = player->m_flLastBoneSetupTime();
			if (i >= 1 && i <= 64)
				previous_bone_cache = historical_bone_cache[i];
			memcpy(layers[LAYERS_ORIGINAL], player->get_animation_layer().get(), player->get_animation_layers_count() * sizeof(AnimationLayer));
		}

		if (store_extra)
			invalid = false;
		backup = store_extra;
		immune = player->m_bGunGameImmunity();
		dormant = player->IsDormant();
		strafing = player->m_bStrafing();
		walking = player->m_bIsWalking();

		flags = player->m_fFlags();
		bone_count = player->m_CachedBoneData().Count();

		simulation_time = player->m_flSimulationTime();
		old_simulation_time = player->m_flOldSimulationTime();
		duck_amount = player->m_flDuckAmount();
		lower_body_yaw_target = player->m_flLowerBodyYawTarget();

		angles = player->m_angEyeAngles();
		abs_angles = player->GetAbsAngles();
		velocity = player->m_vecVelocity();
		origin = player->m_vecOrigin();
		render_origin = store_extra ? player->GetAbsOrigin() : player->m_vecOrigin();
		collision_change_time = player->m_flCollisionChangeTime();
		collision_change_origin = player->m_flCollisionChangeOrigin();
		recent_bone_counter = player->m_iMostRecentModelBoneCounter();

		auto collideable = crypt_ptr <ICollideable> (player->GetCollideable());

		if (collideable)
		{
			mins = collideable->OBBMins();
			maxs = collideable->OBBMaxs();
		}

		animation_state = *player->get_animation_state().get();
	}

	virtual bool can_apply(int matrix_index = MATRIX_MAIN, bool backup = false)
	{
		if (i < 1 || i > 64)
			return false;
		auto player = crypt_ptr <Player> ((Player*)entitylist->GetClientEntity(i));
		if (!player || !player->valid())
			return false;
		if (matrix_index < MATRIX_MAIN || matrix_index >= MATRIX_MAX || bone_count < 0 || bone_count > MAXSTUDIOBONES ||
			bone_count > player->m_CachedBoneData().NumAllocated() ||
			(bone_count > 0 && (!player->m_CachedBoneData().Base() || !(matrix_ready & (1u << matrix_index)))) ||
			(!backup && (bone_count == 0 || !(matrix_mask[matrix_index] & BONE_USED_BY_HITBOX))))
			return false;
		return true;
	}

	virtual bool apply(int matrix_index = MATRIX_MAIN, bool backup = false)
	{
		if (i < 1 || i > 64)
			return false;
		auto player = crypt_ptr <Player> ((Player*)entitylist->GetClientEntity(i));
		if (!player || !player->valid())
		{
			if (backup)
				historical_bone_cache[i] = {};
			return false;
		}
		const auto cache_ready = can_apply(matrix_index, backup);
		if (!cache_ready && !backup)
			return false;

		player->m_angEyeAngles() = angles;
		player->set_abs_angles(abs_angles);
		player->m_vecOrigin() = origin;
		player->set_abs_origin(backup ? render_origin : origin);
		player->set_collision_bounds(mins, maxs, true);
		if (backup)
		{
			player->m_flCollisionChangeTime() = collision_change_time;
			player->m_flCollisionChangeOrigin() = collision_change_origin;
		}

		memcpy(player->get_animation_layer().get(), layers[LAYERS_ORIGINAL], player->get_animation_layers_count() * sizeof(AnimationLayer));

		if (cache_ready)
		{
			player->m_CachedBoneData().m_Size = bone_count;
			if (bone_count > 0)
				memcpy(player->m_CachedBoneData().Base(), matrix[matrix_index], bone_count * sizeof(matrix3x4_t));

			if (!backup)
			{
				const auto current_backup_curtime = globals->curtime;
				globals->curtime = TICKS_TO_TIME(ctx->local()->m_nTickBase());
				((void(__thiscall*)(void*, void*, int))signatures_manager->signatures[SIGNATURE_MODIFY_BONES])(player.get(), player->m_CachedBoneData().Base(), BONE_USED_BY_HITBOX);
				globals->curtime = current_backup_curtime;
			}
		}
		if (!cache_ready)
		{
			// Restore the original pose, but invalidate a cache whose allocation changed.
			player->m_iMostRecentModelBoneCounter() = player->m_iModelBoneCounter() - 1;
			player->m_BoneAccessor().m_ReadableBones = 0;
			player->m_BoneAccessor().m_WritableBones = 0;
			player->m_flLastBoneSetupTime() = -FLT_MAX;
			historical_bone_cache[i] = {};
			return false;
		}

		player->m_iMostRecentModelBoneCounter() = backup ? recent_bone_counter : player->m_iModelBoneCounter();
		player->m_BoneAccessor().m_ReadableBones = backup ? readable_bones : matrix_mask[matrix_index];
		player->m_BoneAccessor().m_WritableBones = backup ? writable_bones : matrix_mask[matrix_index];
		player->m_flLastBoneSetupTime() = backup ? last_bone_setup_time : simulation_time;
		historical_bone_cache[i] = backup ? previous_bone_cache : HistoricalBoneCache{ player.get(), matrix_mask[matrix_index] };
		return true;
	}

	virtual bool valid(bool extra_checks = true, float limit = 0.2f, bool visual = false, int validation_tickbase = -1)
	{
		auto player = crypt_ptr <Player> ((Player*)entitylist->GetClientEntity(i));

		if (!player->valid())
			return false;

		if (invalid)
			return false;
		if (!(matrix_ready & (1u << MATRIX_MAIN)))
			return false;

		if (immune)
			return false;

		if (dormant)
			return false;

		if (!extra_checks)
			return true;

		if (!convars_manager->convars[CONVAR_CL_LAGCOMPENSATION]->GetBool())
			return true;

		auto latency = 0.0f;

		if (visual)
		{
			auto net_channel_info = engine->GetNetChannelInfo();

			if (net_channel_info)
				latency = clamp(net_channel_info->GetLatency(FLOW_OUTGOING) + net_channel_info->GetLatency(FLOW_INCOMING), 0.0f, 1.0f);
		}
		else
			latency = clamp(TICKS_TO_TIME(engine_prediction->latency), 0.0f, 1.0f);

		auto correct = 0.0f;

		if (visual)
		{
			auto update_rate = clamp(convars_manager->convars[CONVAR_CL_UPDATERATE]->GetFloat(), convars_manager->convars[CONVAR_SV_MINUPDATERATE]->GetFloat(), convars_manager->convars[CONVAR_SV_MAXUPDATERATE]->GetFloat());
			auto lerp_ratio = clamp(convars_manager->convars[CONVAR_CL_INTERP_RATIO]->GetFloat(), convars_manager->convars[CONVAR_SV_CLIENT_MIN_INTERP_RATIO]->GetFloat(), convars_manager->convars[CONVAR_SV_CLIENT_MAX_INTERP_RATIO]->GetFloat());
			auto interpolation = clamp(lerp_ratio / update_rate, convars_manager->convars[CONVAR_CL_INTERP]->GetFloat(), 1.0f);

			correct = clamp(latency + interpolation, 0.0f, convars_manager->convars[CONVAR_SV_MAXUNLAG]->GetFloat());
		}
		else
			correct = clamp(latency + ctx->interpolation, 0.0f, convars_manager->convars[CONVAR_SV_MAXUNLAG]->GetFloat());

		auto delta_time = 0.0f;

		if (visual)
			delta_time = correct - (globals->curtime - simulation_time);
		else
		{
			auto tickbase = validation_tickbase >= 0 ? validation_tickbase : ctx->tickbase;
			delta_time = correct - (TICKS_TO_TIME(tickbase) - simulation_time);
		}

		if (abs(delta_time) >= limit)
			return false;

		auto extra_choke = 0;

		if (!visual && ctx->fake_ducking)
			extra_choke = 14 - clientstate->m_nChokedCommands;

		auto server_tickcount = globals->tickcount + TIME_TO_TICKS(latency) + extra_choke;
		auto dead_time = (int)(float)((float)((int)((float)((float)server_tickcount * globals->intervalpertick) - 0.2f) / globals->intervalpertick) + 0.5f);

		if (TIME_TO_TICKS(simulation_time + ctx->interpolation) < dead_time)
			return false;

		return true;
	}
};

class PlayerData
{
public:
	float simulation_time;
	float simulation_time_old;
	float max_previous_simtime;
	float last_loop_cycle;
	float last_loop_rate;
	float goal_feet_yaw;
	AnimationState animation_state;
	Player* animation_player;
	float animation_spawn_time;
	bool animation_initialized;

	PlayerData()
	{
		reset();
	}

	void reset()
	{
		simulation_time = 0.0f;
		simulation_time_old = 0.0f;
		max_previous_simtime = 0.0f;
		last_loop_cycle = 0.0f;
		last_loop_rate = 0.0f;
		goal_feet_yaw = 0.0f;
		animation_state = AnimationState();
		animation_player = nullptr;
		animation_spawn_time = 0.0f;
		animation_initialized = false;
	}
};

class Animations
{
public:
	deque <AnimationData> animation_data[65];
	PlayerData player_data[65];

	void resolver_yaw(crypt_ptr <Player> player, crypt_ptr <AnimationData> record, crypt_ptr <AnimationData> previous);
	virtual bool update(crypt_ptr <Player> player, crypt_ptr <AnimationData> data);
	virtual void run();
};
