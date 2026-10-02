#pragma once

// A temporary historical cache is deliberately narrower than engine SetupBones.
// Requests for other masks must fail without rebuilding the target's current pose.
struct HistoricalBoneCache
{
	const void* player = nullptr;
	int mask = 0;
	float spawn_time = 0.0f;
	const void* model = nullptr;
};

inline HistoricalBoneCache historical_bone_cache[65];
