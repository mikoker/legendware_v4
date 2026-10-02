// This is an independent project of an individual developer. Dear PVS-Studio, please check it.
// PVS-Studio Static Code Analyzer for C, C++, C#, and Java: http://www.viva64.com

#include "hooks.h"
#include "..\features\features.h"
#include "..\features\animations.h"
#include "..\render.h"

void __fastcall hooked_updateclientsideanimation(Player* player, void* edx)
{
	if (!player)
		return ((UpdateClientSideAnimation)original_updateclientsideanimation)(player);

	if (!player->valid())
		return ((UpdateClientSideAnimation)original_updateclientsideanimation)(player);

	if (ctx->updating_animation)
		return ((UpdateClientSideAnimation)original_updateclientsideanimation)(player);

	if (player == ctx->local().get())
		local_animations->render();
	else if (!animations->animation_data[player->EntIndex()].empty())
	{
		auto front = crypt_ptr <AnimationData> (&animations->animation_data[player->EntIndex()].front());

		if (front->dormant)
			return;
		if (historical_bone_cache[player->EntIndex()].player == player &&
			historical_bone_cache[player->EntIndex()].spawn_time == player->m_flSpawnTime() &&
			historical_bone_cache[player->EntIndex()].model == player->GetModel())
			return;
		if (!front->matches_player(player) || !(front->matrix_ready & (1u << MATRIX_VISUAL_INTERPOLATED)) || front->bone_count <= 0 ||
			front->bone_count > MAXSTUDIOBONES || !player->m_CachedBoneData().Base() ||
			front->bone_count > player->m_CachedBoneData().NumAllocated())
			return ((UpdateClientSideAnimation)original_updateclientsideanimation)(player);
		if (front->render_origin != player->GetAbsOrigin())
		{
			for (auto i = 0; i < front->bone_count; ++i)
			{
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][0][3] -= front->render_origin.x;
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][1][3] -= front->render_origin.y;
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][2][3] -= front->render_origin.z;
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][0][3] += player->GetAbsOrigin().x;
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][1][3] += player->GetAbsOrigin().y;
				front->matrix[MATRIX_VISUAL_INTERPOLATED][i][2][3] += player->GetAbsOrigin().z;
			}
		}

		front->render_origin = player->GetAbsOrigin();
		memcpy(player->m_CachedBoneData().Base(), front->matrix[MATRIX_VISUAL_INTERPOLATED], front->bone_count * sizeof(matrix3x4_t));
		player->m_CachedBoneData().m_Size = front->bone_count;
		player->m_BoneAccessor().m_ReadableBones = front->matrix_mask[MATRIX_VISUAL_INTERPOLATED];
		player->m_BoneAccessor().m_WritableBones = front->matrix_mask[MATRIX_VISUAL_INTERPOLATED];
		player->m_iMostRecentModelBoneCounter() = player->m_iModelBoneCounter();
		player->m_flLastBoneSetupTime() = front->simulation_time;
		player->attachment_helper();
	}
	else
		return ((UpdateClientSideAnimation)original_updateclientsideanimation)(player);
}
