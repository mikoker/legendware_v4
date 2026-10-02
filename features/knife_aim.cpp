// This is an independent project of an individual developer. Dear PVS-Studio, please check it.
// PVS-Studio Static Code Analyzer for C, C++, C#, and Java: http://www.viva64.com

#include "knife_aim.h"
#include "logs.h"
#include "exploits.h"

void KnifeAim::run(crypt_ptr <CUserCmd> cmd)
{
	if (ctx->weapon_config != WEAPON_CONFIG_KNIFE)
		return;

	backup.clear();
	targets.clear();
	final_target.reset();

	prepare();
	scan();
	fire(cmd);

	for (auto& data : backup)
		data.apply(MATRIX_MAIN, true);
}

void KnifeAim::prepare()
{
	for (auto i = 1; i <= globals->maxclients; ++i)
	{
		auto player = crypt_ptr <Player> ((Player*)entitylist->GetClientEntity(i));

		if (player.get() == ctx->local().get())
			continue;

		if (!player->valid(!ctx->friendly_fire))
			continue;

		if (animations->animation_data[i].empty())
			continue;

		if (config->player_list.player_settings[i].ignore)
			continue;

		targets.emplace_back(PreparedTarget(i, player));
	}
}

void KnifeAim::scan()
{
	auto best_distance = FLT_MAX;

	for (auto& target : targets)
	{
		crypt_ptr <AnimationData> data;

		for (auto i = 0; i < target.data->size(); ++i)
		{
			auto current_data = crypt_ptr <AnimationData> (&target.data->at(i));

			if (!current_data->valid())
				continue;

			if (current_data->old_simulation_time <= 0.0f)
				continue;

			if (current_data->old_simulation_time > current_data->simulation_time)
				continue;

			auto distance = current_data->origin.DistTo(ctx->shoot_position);

			if (distance < best_distance)
			{
				best_distance = distance;
				data = current_data;
			}
		}

		if (!data)
			continue;

		auto found_backup = false;

		for (auto& backup_data : backup)
		{
			if (backup_data.i == target.index)
			{
				found_backup = true;
				break;
			}
		}

		if (!found_backup)
		{
			backup.emplace_back(AnimationData(target.player));
			if (!backup.back().can_apply(MATRIX_MAIN, true))
			{
				backup.pop_back();
				continue;
			}
		}

		final_target.player = target.player;
		final_target.data = data;
	}
}

static bool trace_knife_attack(Player* target, const Vector& delta, bool stab)
{
	auto direction = delta;
	const auto length = direction.Length();
	if (!std::isfinite(length) || length <= 0.0f)
		return false;
	direction /= length;
	const auto end = ctx->shoot_position + direction * (stab ? 32.0f : 48.0f);
	CTraceFilter filter;
	filter.pSkip = ctx->local().get();
	CGameTrace trace;
	Ray_t ray;
	ray.Init(ctx->shoot_position, end);
	enginetrace->TraceRay(ray, MASK_SOLID, &filter, &trace);
	if (trace.fraction >= 1.0f)
	{
		ray.Init(ctx->shoot_position, end, Vector(-16.0f, -16.0f, -18.0f), Vector(16.0f, 16.0f, 18.0f));
		enginetrace->TraceRay(ray, MASK_SOLID, &filter, &trace);
	}
	return trace.hit_entity == target;
}

void KnifeAim::fire(crypt_ptr <CUserCmd> cmd)
{
	if (!cmd || !final_target.data || !final_target.player || !ctx->weapon())
		return;

	const auto attack_time = TICKS_TO_TIME(ctx->tickbase);
	if (ctx->local()->m_fFlags() & FL_FROZEN || attack_time < ctx->local()->m_flNextAttack())
		return;

	if (!config->rage.automatic_fire && !(cmd->buttons & IN_ATTACK) && !(cmd->buttons & IN_ATTACK2))
		return;

	if (!final_target.data->apply())
		return;

	auto mins = final_target.data->origin + final_target.data->mins;
	auto maxs = final_target.data->origin + final_target.data->maxs;

	if (mins.x > maxs.x || mins.y > maxs.y || mins.z > maxs.z)
		return;
	const auto aim_point = Vector(clamp(ctx->shoot_position.x, mins.x, maxs.x),
		clamp(ctx->shoot_position.y, mins.y, maxs.y), clamp(ctx->shoot_position.z, mins.z, maxs.z));
	auto delta = aim_point - ctx->shoot_position;

	auto fired = false;
	const auto manual_attack = (cmd->buttons & (IN_ATTACK | IN_ATTACK2)) != 0;
	auto stab = (cmd->buttons & IN_ATTACK2) != 0;
	if (!manual_attack)
	{
		auto to_target = final_target.data->origin - ctx->local()->m_vecOrigin();
		to_target.z = 0.0f;
		to_target.NormalizeInPlace();
		Vector forward;
		math::angle_vectors(final_target.data->abs_angles, &forward, nullptr, nullptr);
		forward.z = 0.0f;
		const auto behind = to_target.Dot(forward) > 0.475f;
		const auto armored = final_target.player->m_ArmorValue() > 0;
		const auto first_swing = ctx->weapon()->m_flNextPrimaryAttack() + 0.4f < attack_time;
		// Damage values follow the comparison source; geometry is verified against csgo_legacy.
		const auto swing_damage = behind ? (armored ? 76 : 90) : (first_swing ? (armored ? 34 : 40) : (armored ? 21 : 25));
		const auto followup_damage = behind ? (armored ? 76 : 90) : (armored ? 21 : 25);
		const auto stab_damage = behind ? (armored ? 153 : 180) : (armored ? 55 : 65);
		const auto health = final_target.player->m_iHealth();
		stab = health > swing_damage && (health <= stab_damage || health > swing_damage + followup_damage + stab_damage);
	}
	const auto can_attack = [&](bool secondary)
	{
		const auto next_attack = secondary ? ctx->weapon()->m_flNextSecondaryAttack() : ctx->weapon()->m_flNextPrimaryAttack();
		return attack_time >= next_attack && trace_knife_attack(final_target.player.get(), delta, secondary);
	};
	if (!can_attack(stab))
	{
		if (manual_attack || !stab || !can_attack(false))
			return;
		stab = false;
	}
	if (!manual_attack)
		cmd->buttons |= stab ? IN_ATTACK2 : IN_ATTACK;
	cmd->viewangles = delta.ToEulerAngles();
	cmd->tickcount = TIME_TO_TICKS(final_target.data->simulation_time + ctx->interpolation);
	if (!config->rage.silent)
		engine->SetViewAngles(cmd->viewangles);
	fired = true;

#if BETA
	if (fired)
	{
		auto original_tickbase = ctx->tickbase;

		if (exploits->hide_shots || exploits->double_tap)
			original_tickbase += exploits->target_tickbase_shift;

		auto correct = clamp(TICKS_TO_TIME(engine_prediction->latency) + ctx->interpolation, 0.0f, convars_manager->convars[CONVAR_SV_MAXUNLAG]->GetFloat());
		auto delta_time = correct - (TICKS_TO_TIME(original_tickbase) - final_target.data->simulation_time);
		auto backtrack_ticks = TIME_TO_TICKS(abs(delta_time));

		string log;

		player_info_t player_info;
		engine->GetPlayerInfo(final_target.data->i, &player_info);

		log += crypt_str("Fired shot at ") + (string)player_info.szName;
		log += crypt_str(", backtrack: ") + to_string(backtrack_ticks);
		log += crypt_str(", choke: ") + to_string(TIME_TO_TICKS(final_target.data->simulation_time - final_target.data->old_simulation_time));

		logs->add(log, Color::LightBlue, crypt_str("[ SHOT ] "));
	}
#endif
}
