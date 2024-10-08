import math

class PARAMS:
    prev_speed = None
    prev_steering_angle = None 
    prev_steps = None
    prev_direction_diff = None
    prev_normalized_distance_from_route = None
    unpardonable_action = False
    intermediate_progress = [0] * 11

def reward_function(params):

    # Constants
    MAX_REWARD = 1e3
    OFF_TRACK_PENALTY_MIN = 0.1
    OFF_TRACK_PENALTY_THRESHOLD = 0.5

    # Read input parameters
    heading = params['heading']
    distance_from_center = params['distance_from_center']
    steps = params['steps']
    steering_angle = params['steering_angle']
    speed = params['speed']
    progress = params.get('progress', 0)
    normalized_car_distance_from_route = params.get('normalized_car_distance_from_route', 0)
    vehicle_x = params['x']
    vehicle_y = params['y']
    waypoints = params['waypoints']
    closest_waypoints = params['closest_waypoints']
    is_turn_upcoming = params.get('is_turn_upcoming', False)
    all_wheels_on_track = params['all_wheels_on_track']
    wheels_on_track = params.get('wheels_on_track', 4)
    track_width = params.get('track_width', 1.0)  # Example default value

    # Calculate the next waypoint
    next_point = waypoints[closest_waypoints[1]]

    # Determine track section
    track_section = get_track_section(waypoints, closest_waypoints)

    # Adaptive Speed Reward (Suggestion 1)
    speed_reward = calculate_adaptive_speed_reward(speed, track_section, waypoints, closest_waypoints)

    # Lateral Distance Reward Scaling (Suggestion 2)
    lateral_distance_reward = calculate_lateral_distance_reward(distance_from_center, track_width)

    # Off-Track Penalty
    off_track_penalty = max(OFF_TRACK_PENALTY_MIN, 1 - abs(normalized_car_distance_from_route))
    
    # Heading Reward
    heading_reward = calculate_heading_reward(heading, vehicle_x, vehicle_y, next_point)

    # Curvature-based Reward Adjustment (Suggestion 3)
    curvature_reward = calculate_curvature_reward(waypoints, closest_waypoints, speed)

    # Intermediate Progress Bonus Normalization (Suggestion 4)
    intermediate_progress_bonus = calculate_intermediate_progress_bonus(progress, steps, track_width)

    # Steering Angle Maintenance Bonus Scaling (Suggestion 5)
    steering_angle_bonus = calculate_steering_angle_bonus(steering_angle, speed, is_turn_upcoming)

    # Adaptive Time Penalty (Suggestion 6)
    adaptive_time_penalty = calculate_adaptive_time_penalty(steps, distance_from_center, track_width, speed, progress)

    # Wheel-off-track Penalty Scaling (Suggestion 7)
    wheel_off_track_penalty = calculate_wheel_off_track_penalty(all_wheels_on_track, wheels_on_track, distance_from_center)

    # Total reward calculation with weighted components
    total_reward = (
        0.3 * speed_reward +
        0.2 * lateral_distance_reward +
        0.2 * heading_reward +
        0.2 * curvature_reward +
        0.1 * intermediate_progress_bonus +
        steering_angle_bonus
    ) * off_track_penalty - adaptive_time_penalty - wheel_off_track_penalty

    # Reward Normalization (Suggestion 8)
    total_reward = normalize_reward(total_reward, progress, speed, track_width, steps)

    # Unpardonable Action Penalty (Suggestion 9)
    if PARAMS.unpardonable_action:
        return -MAX_REWARD

    # Reward Clipping (Suggestion 10)
    total_reward = min(max(total_reward, -MAX_REWARD), MAX_REWARD)

    return total_reward


def get_track_section(waypoints, closest_waypoints):
    next_point = waypoints[closest_waypoints[1]]
    prev_point = waypoints[closest_waypoints[0]]
    
    dx = next_point[0] - prev_point[0]
    dy = next_point[1] - prev_point[1]
    angle = math.atan2(dy, dx)

    # Here, you can decide the threshold for straight vs. curve
    curvature_threshold = 0.4  # Adjust this value based on your track

    if abs(angle) < curvature_threshold:
        return 'straight'
    else:
        return 'curve'


def calculate_adaptive_speed_reward(speed, track_section, waypoints, closest_waypoints):
    # Adaptive Speed Reward with a refined sigmoid function (Suggestion 1)
    optimal_speeds = { 'straight': 4.0, 'curve': 3.0 }  # Example speeds for different track sections
    optimal_speed = optimal_speeds.get(track_section, 3.5)

    # Adjust optimal speed based on upcoming curvature
    next_point = waypoints[closest_waypoints[1]]
    prev_point = waypoints[closest_waypoints[0]]
    dx = next_point[0] - prev_point[0]
    dy = next_point[1] - prev_point[1]
    curvature = math.atan2(dy, dx)
    optimal_speed -= abs(curvature) * 0.5  # Adjust optimal speed based on curvature

    speed_reward = 1 / (1 + math.exp(-(speed - optimal_speed) / 0.3))  # Adjusted parameter
    speed_reward = max(0, min(speed_reward, 1))  # Clipping between 0 and 1
    return speed_reward


def calculate_lateral_distance_reward(distance_from_center, track_width):
    # Non-linear scaling for lateral distance reward with adjusted exponent (Suggestion 2)
    return max(0, 1 - (2 * abs(distance_from_center) / track_width) ** 1.5)  # Adjusted exponent


def calculate_curvature_reward(waypoints, closest_waypoints, speed):
    # Refine curvature reward based on upcoming turns and speed (Suggestion 3)
    next_point = waypoints[closest_waypoints[1]]
    prev_point = waypoints[closest_waypoints[0]]
    
    dx = next_point[0] - prev_point[0]
    dy = next_point[1] - prev_point[1]
    curvature = math.atan2(dy, dx)
    
    if abs(curvature) < math.pi / 8:
        return 1.0
    elif math.pi / 8 <= abs(curvature) < math.pi / 4:
        return 1.5 if speed < 2.5 else 1.0
    else:
        return max(0, 1 - abs(curvature) / (math.pi / 4) * (speed / 4))


def calculate_intermediate_progress_bonus(progress, steps, track_width):
    # Normalize intermediate progress bonus by track complexity and overall performance (Suggestion 4)
    progress_reward = 10 * progress / steps
    if steps <= 5:
        progress_reward = 1  # Ignore progress in the first 5 steps
    
    intermediate_progress_bonus = 0
    pi = int(progress // 10)
    if pi != 0 and PARAMS.intermediate_progress[pi] == 0:
        intermediate_progress_bonus = progress_reward ** (1 + 0.5 * pi / (steps / track_width))
        PARAMS.intermediate_progress[pi] = intermediate_progress_bonus
    
    return intermediate_progress_bonus


def calculate_steering_angle_bonus(steering_angle, speed, is_turn_upcoming):
    # Scale steering angle bonus based on speed and upcoming turns (Suggestion 5)
    if PARAMS.prev_steering_angle is not None:
        STEERING_ANGLE_MAINTAIN_BONUS_MULTIPLIER = 2
        angle_diff = abs(steering_angle - PARAMS.prev_steering_angle)
        steering_angle_bonus = max(0, 1 - angle_diff / 10) * (STEERING_ANGLE_MAINTAIN_BONUS_MULTIPLIER * (speed / 4))
        if is_turn_upcoming:
            steering_angle_bonus *= 1.2  # Increase bonus if a turn is upcoming
    else:
        steering_angle_bonus = 0
    
    PARAMS.prev_steering_angle = steering_angle
    return steering_angle_bonus


def calculate_adaptive_time_penalty(steps, distance_from_center, track_width, speed, progress):
    TIME_PENALTY_FACTOR = 0.01  
    # Adaptive time penalty based on distance from track center and other factors (Suggestion 6)
    time_penalty = TIME_PENALTY_FACTOR * steps
    if distance_from_center > track_width / 4:
        time_penalty *= 1 + (distance_from_center - track_width / 4) / (track_width / 4)
    if speed < 1.0:
        time_penalty *= 1.5  # Increase penalty for low speed
    if progress < 10:
        time_penalty *= 1.2  # Increase penalty for low progress
    return time_penalty


def calculate_wheel_off_track_penalty(all_wheels_on_track, wheels_on_track, distance_from_center):
    # Scale penalty based on the number of wheels off the track and distance from track edge (Suggestion 7)
    if all_wheels_on_track:
        return 0
    elif wheels_on_track == 3:
        return 0.1
    elif wheels_on_track == 2:
        return 0.25
    elif wheels_on_track == 1:
        return 0.5
    else:
        return 1.0 + distance_from_center  # Heavy penalty if all wheels are off the track, scaled by distance


def normalize_reward(total_reward, progress, speed, track_width, steps):
    # Normalize reward based on various factors including consistency (Suggestion 8)
    progress_factor = (progress + 1e-3) ** 2
    speed_factor = (speed + 1e-3) ** 2
    track_complexity_factor = max(0.5, track_width / 5 + steps / 100)
    consistency_factor = 1.0  # Placeholder for consistency factor
    
    return total_reward / (progress_factor * speed_factor * track_complexity_factor * consistency_factor)


def calculate_direction_diff(heading, vehicle_x, vehicle_y, next_point):
    next_point_x = next_point[0]
    next_point_y = next_point[1]

    # Calculate the direction in radians, arctan2(dy, dx), the result is (-pi, pi) in radians between target and current vehicle position
    route_direction = math.atan2(next_point_y - vehicle_y, next_point_x - vehicle_x)
    # Convert to degrees
    route_direction = math.degrees(route_direction)
    # Calculate the difference between the track direction and the heading direction of the car
    direction_diff = route_direction - heading
    return direction_diff


def calculate_heading_reward(heading, vehicle_x, vehicle_y, next_point):
    next_point_x = next_point[0]
    next_point_y = next_point[1]

    # Calculate the direction in radians, arctan2(dy, dx), the result is (-pi, pi) in radians between target and current vehicle position
    route_direction = math.atan2(next_point_y - vehicle_y, next_point_x - vehicle_x)
    # Convert to degrees
    route_direction = math.degrees(route_direction)
    # Calculate the difference between the track direction and the heading direction of the car
    direction_diff = route_direction - heading
    # Check that the direction_diff is in valid range
    # Then compute the heading reward
    heading_reward = math.cos(abs(direction_diff) * (math.pi / 180)) ** 10
    if abs(direction_diff) <= 20:
        heading_reward = math.cos(abs(direction_diff) * (math.pi / 180)) ** 4

    return heading_reward