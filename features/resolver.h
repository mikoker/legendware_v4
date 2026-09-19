#pragma once

#include "..\includes.h"

class Player;
class AnimationData;

enum ResolverEvidence
{
	RESOLVER_NONE,
	RESOLVER_MOVING_LAYER,
	RESOLVER_LBY_UPDATE,
	RESOLVER_JITTER,
	RESOLVER_LAST_MOVE,
	RESOLVER_BRUTE_FORCE
};

enum ResolverProfile
{
	RESOLVER_STANDING,
	RESOLVER_ACCELERATING,
	RESOLVER_CRUISING,
	RESOLVER_DECELERATING,
	RESOLVER_RECENTLY_STOPPED,
	RESOLVER_AIR,
	RESOLVER_PROFILE_MAX
};

enum ResolverCandidateSource
{
	RESOLVER_CANDIDATE_BASELINE,
	RESOLVER_CANDIDATE_ZERO,
	RESOLVER_CANDIDATE_POSITIVE,
	RESOLVER_CANDIDATE_POSITIVE_LOW,
	RESOLVER_CANDIDATE_NEGATIVE,
	RESOLVER_CANDIDATE_NEGATIVE_LOW
};

constexpr int RESOLVER_MAX_CANDIDATES = 6;

struct ResolverCandidate
{
	float yaw = 0.0f;
	float score = 0.0f;
	int matrix = 0;
	ResolverCandidateSource source = RESOLVER_CANDIDATE_ZERO;
};

struct ResolverResult
{
	ResolverCandidate candidates[RESOLVER_MAX_CANDIDATES];
	int count = 0;
	int selected = -1;
	int selected_matrix = 0;
	ResolverEvidence evidence = RESOLVER_NONE;
	ResolverProfile profile = RESOLVER_STANDING;
	float confidence = 0.0f;
};

class Resolver
{
	struct CandidateStats
	{
		int hits = 0;
		int misses = 0;
	};

	struct PlayerState
	{
		float last_speed = 0.0f;
		float last_move_yaw = 0.0f;
		float last_move_time = 0.0f;
		float last_lby = 0.0f;
		float last_eye_yaw = 0.0f;
		Vector last_move_origin;
		bool has_last_move = false;
		bool has_lby = false;
		bool has_eye_yaw = false;
		int jitter_ticks = 0;
		CandidateStats stats[RESOLVER_PROFILE_MAX][RESOLVER_MAX_CANDIDATES];
	};

	PlayerState states[65];

	int nearest_candidate(const ResolverResult& result, float yaw) const;
	ResolverProfile get_profile(const AnimationData& record, const AnimationData* previous, PlayerState& state) const;

public:
	void resolve(Player* player, AnimationData& record, const AnimationData* previous, float max_desync);
	void record_hit(int player_index, const ResolverResult& result);
	void record_miss(int player_index, const ResolverResult& result);
	void reset(int player_index);
	void reset();
};
