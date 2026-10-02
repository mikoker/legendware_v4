#pragma once

#include "..\includes.h"
#include "..\data.h"
#include "..\globals.h"

enum
{
	SIDE_REAL,
	SIDE_FAKE,
	SIDE_MAX
};

class LocalAnimations //-V730
{
	bool angle_locked = false;
	bool update_fake_bones = false;

	float last_spawn = 0.0f;
	Vector angle;

	float angles[SIDE_MAX];
	float pose_parameters[SIDE_MAX][24];

	AnimationLayer layers[SIDE_MAX][13];
public:
	float pose_parameters_shoot[24]{};
	AnimationLayer layers_shoot[13]{};
	Player* shoot_player = nullptr;
	float shoot_spawn = 0.0f;
	const void* shoot_model = nullptr;
	int shoot_layer_count = 0;

	bool has_shoot_pose(Player* player) const
	{
		return player && shoot_player == player && shoot_spawn == player->m_flSpawnTime() &&
			shoot_model == player->GetModel() && shoot_layer_count == player->get_animation_layers_count();
	}

	Vector sent_angle;
	AnimationState fake_animstate;

	virtual void render();
	virtual void run(crypt_ptr <CUserCmd> cmd, bool send_packet);
};
