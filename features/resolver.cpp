#include "resolver.h"
#include "animations.h"
#include "..\globals.h"

int Resolver::nearest_candidate(const ResolverResult& result, float yaw) const
{
	auto best = -1;
	auto best_delta = FLT_MAX;

	for (auto i = 0; i < result.count; ++i)
	{
		auto delta = fabsf(math::angle_diff(yaw, result.candidates[i].yaw));
		if (delta < best_delta)
		{
			best = i;
			best_delta = delta;
		}
	}

	return best;
}

ResolverProfile Resolver::get_profile(const AnimationData& record, const AnimationData* previous, PlayerState& state) const
{
	if (!(record.network.flags & FL_ONGROUND))
		return RESOLVER_AIR;

	auto speed = record.velocity.Length2D();
	if (speed <= 0.1f)
	{
		if (state.has_last_move && record.simulation_time - state.last_move_time <= 1.0f)
			return RESOLVER_RECENTLY_STOPPED;

		return RESOLVER_STANDING;
	}

	auto previous_speed = previous ? previous->velocity.Length2D() : state.last_speed;
	auto speed_delta = speed - previous_speed;
	if (speed_delta > 5.0f)
		return RESOLVER_ACCELERATING;
	if (speed_delta < -5.0f)
		return RESOLVER_DECELERATING;

	return RESOLVER_CRUISING;
}

void Resolver::resolve(Player* player, AnimationData& record, const AnimationData* previous, float max_desync)
{
	auto& result = record.resolver;
	result = ResolverResult();
	record.resolver_type = RESOLVER_NONE;
	record.resolver_side = MATRIX_MAIN;

	if (!player || record.i <= 0 || record.i >= 65)
		return;

	auto eye_yaw = math::normalize_yaw(record.network.angles.y);
	const struct
	{
		ResolverCandidateSource source;
		int matrix;
		float scale;
		bool baseline;
	} candidates[] =
	{
		{ RESOLVER_CANDIDATE_BASELINE, MATRIX_BASELINE, 0.0f, true },
		{ RESOLVER_CANDIDATE_ZERO, MATRIX_ZERO, 0.0f, false },
		{ RESOLVER_CANDIDATE_POSITIVE, MATRIX_FIRST, 1.0f, false },
		{ RESOLVER_CANDIDATE_POSITIVE_LOW, MATRIX_FIRST_LOW, 0.5f, false },
		{ RESOLVER_CANDIDATE_NEGATIVE, MATRIX_SECOND, -1.0f, false },
		{ RESOLVER_CANDIDATE_NEGATIVE_LOW, MATRIX_SECOND_LOW, -0.5f, false }
	};

	for (const auto& candidate : candidates)
	{
		auto& out = result.candidates[result.count++];
		out.source = candidate.source;
		out.matrix = candidate.matrix;
		out.yaw = candidate.baseline ? record.animation_state.goal_feet_yaw : math::normalize_yaw(eye_yaw + max_desync * candidate.scale);
	}
	result.selected = 0;
	result.selected_matrix = MATRIX_BASELINE;

	if (!config->rage.enable || !ctx->local()->valid() || record.exploit ||
		(player->m_iTeamNum() == ctx->local()->m_iTeamNum() && !ctx->friendly_fire))
		return;

	auto& state = states[record.i];
	result.profile = get_profile(record, previous, state);
	auto speed = record.velocity.Length2D();
	auto moving = result.profile == RESOLVER_ACCELERATING || result.profile == RESOLVER_CRUISING || result.profile == RESOLVER_DECELERATING;
	auto lby_updated = state.has_lby && fabsf(math::angle_diff(record.network.lower_body_yaw, state.last_lby)) > 1.0f;

	if (!state.has_lby || lby_updated)
	{
		state.last_lby = record.network.lower_body_yaw;
		state.has_lby = true;
	}

	if (moving)
	{
		state.last_move_yaw = record.network.lower_body_yaw;
		state.last_move_time = record.simulation_time;
		state.last_move_origin = record.network.origin;
		state.has_last_move = true;
	}

	for (auto i = 0; i < result.count; ++i)
	{
		auto& candidate = result.candidates[i];
		auto& stats = state.stats[result.profile][i];
		auto attempts = stats.hits + stats.misses;
		if (attempts > 0)
			candidate.score += (float)(stats.hits - stats.misses) / (float)attempts * 2.0f;

		auto layer_index = candidate.matrix == MATRIX_ZERO ? LAYERS_ZERO :
			candidate.matrix == MATRIX_FIRST ? LAYERS_FIRST :
			candidate.matrix == MATRIX_SECOND ? LAYERS_SECOND : -1;

		if (moving && layer_index >= 0)
		{
			auto& layer = record.layers[layer_index][6];
			if (layer.m_nSequence == record.server_layers[6].m_nSequence)
			{
				auto cycle_delta = fabsf(layer.m_flCycle - record.server_layers[6].m_flCycle);
				cycle_delta = min(cycle_delta, 1.0f - cycle_delta);
				auto error = fabsf(layer.m_flPlaybackRate - record.server_layers[6].m_flPlaybackRate) * 2.0f +
					fabsf(layer.m_flWeight - record.server_layers[6].m_flWeight) + cycle_delta;
				candidate.score += max(0.0f, 2.0f - error * (record.choke > 2 ? 8.0f : 16.0f));
			}
		}
	}

	if ((record.network.flags & FL_ONGROUND) && lby_updated && fabsf(math::angle_diff(record.network.lower_body_yaw, eye_yaw)) >= 20.0f)
	{
		auto candidate = nearest_candidate(result, record.network.lower_body_yaw);
		if (candidate >= 0)
			result.candidates[candidate].score += 3.0f;
		result.evidence = RESOLVER_LBY_UPDATE;
	}
	else if (result.profile == RESOLVER_RECENTLY_STOPPED && state.has_last_move &&
		(record.network.origin - state.last_move_origin).Length2D() <= 64.0f)
	{
		auto candidate = nearest_candidate(result, state.last_move_yaw);
		if (candidate >= 0)
			result.candidates[candidate].score += max(0.0f, 2.0f - (record.simulation_time - state.last_move_time) * 2.0f);
		result.evidence = RESOLVER_LAST_MOVE;
	}
	else if (moving)
		result.evidence = RESOLVER_MOVING_LAYER;

	auto eye_delta = state.has_eye_yaw ? math::angle_diff(eye_yaw, state.last_eye_yaw) : 0.0f;
	state.jitter_ticks = fabsf(eye_delta) >= 35.0f ? min(state.jitter_ticks + 1, 4) : 0;
	state.last_eye_yaw = eye_yaw;
	state.has_eye_yaw = true;

	if ((record.network.flags & FL_ONGROUND) && state.jitter_ticks >= 2)
	{
		for (auto i = 0; i < result.count; ++i)
			if (result.candidates[i].source == RESOLVER_CANDIDATE_POSITIVE || result.candidates[i].source == RESOLVER_CANDIDATE_NEGATIVE)
				result.candidates[i].score += 0.5f;
		if (result.evidence == RESOLVER_NONE)
			result.evidence = RESOLVER_JITTER;
	}

	auto best = 0;
	auto second_score = -FLT_MAX;
	for (auto i = 1; i < result.count; ++i)
	{
		if (result.candidates[i].score > result.candidates[best].score)
		{
			second_score = result.candidates[best].score;
			best = i;
		}
		else
			second_score = max(second_score, result.candidates[i].score);
	}

	result.selected = best;
	result.selected_matrix = result.candidates[best].matrix;
	result.confidence = clamp(result.candidates[best].score - second_score, 0.0f, 4.0f) * 0.25f;
	if (result.evidence != RESOLVER_LBY_UPDATE)
	{
		auto& stats = state.stats[result.profile][best];
		if (stats.hits || stats.misses)
			result.evidence = RESOLVER_BRUTE_FORCE;
	}
	record.resolver_type = result.evidence;
	record.resolver_side = result.selected_matrix;
	state.last_speed = speed;
}

void Resolver::record_hit(int player_index, const ResolverResult& result)
{
	if (player_index <= 0 || player_index >= 65 || result.selected < 0 || result.selected >= result.count)
		return;

	auto& stats = states[player_index].stats[result.profile][result.selected];
	stats.hits = min(stats.hits + 1, 8);
	stats.misses = max(stats.misses - 1, 0);
}

void Resolver::record_miss(int player_index, const ResolverResult& result)
{
	if (player_index <= 0 || player_index >= 65 || result.selected < 0 || result.selected >= result.count)
		return;

	auto& selected = states[player_index].stats[result.profile][result.selected];
	selected.misses = min(selected.misses + 1, 8);
	selected.hits = max(selected.hits - 1, 0);
}

void Resolver::reset(int player_index)
{
	if (player_index > 0 && player_index < 65)
		states[player_index] = PlayerState();
}

void Resolver::reset()
{
	for (auto i = 0; i < 65; ++i)
		states[i] = PlayerState();
}
