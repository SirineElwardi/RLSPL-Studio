"""Initial RLSPL component catalog derived from the revised domain model."""

from __future__ import annotations

from pathlib import Path

from .descriptors import (
    AlgorithmComposition,
    AlgorithmDescriptor,
    AlgorithmRequirements,
    AlgorithmRuntimeAssets,
    BehaviorDescriptor,
    BehaviorRequirements,
    BehaviorRuntimeAssets,
    EnvironmentCapabilities,
    EnvironmentDescriptor,
    EnvironmentRuntimeAssets,
    OptimizerDescriptor,
    OptimizerRequirements,
    OptimizerRuntimeAssets,
    ParameterDefinition,
)
from .models import (
    ActionKind,
    EvaluationActionMode,
    ObservationKind,
    OptimizerInterface,
    ParameterType,
    PolicyInterface,
)
from .registry import ComponentRegistry
from .plugins import discover_plugins


MOUNTAIN_CAR = "gymnasium.mountain_car"
CART_POLE = "gymnasium.cart_pole"
ACROBOT = "gymnasium.acrobot"
LUNAR_LANDER_DISCRETE = "gymnasium.lunar_lander.discrete"
MOUNTAIN_CAR_CONTINUOUS = "gymnasium.mountain_car.continuous"
PENDULUM = "gymnasium.pendulum"
LUNAR_LANDER_CONTINUOUS = "gymnasium.lunar_lander.continuous"
BIPEDAL_WALKER = "gymnasium.bipedal_walker"

Q_LEARNING = "rlspl.q_learning"
DQN = "rlspl.dqn"
DDPG = "rlspl.ddpg"
SAC = "rlspl.sac"

GREEDY = "rlspl.behavior.greedy"
RANDOM_MIXTURE = "rlspl.behavior.random_mixture"
BOLTZMANN = "rlspl.behavior.boltzmann"
DETERMINISTIC = "rlspl.behavior.deterministic"
GAUSSIAN_NOISE = "rlspl.behavior.gaussian_noise"
OU_NOISE = "rlspl.behavior.ou_noise"
PARAMETER_NOISE = "rlspl.behavior.parameter_noise"
ENTROPY_SAMPLING = "rlspl.behavior.entropy_sampling"
ALGORITHM_OWNED = "rlspl.behavior.algorithm_owned"

DIRECT_UPDATE = "rlspl.optimizer.direct_update"
ADAM = "rlspl.optimizer.adam"
RMSPROP = "rlspl.optimizer.rmsprop"
SGD = "rlspl.optimizer.sgd"
ALGORITHM_OWNED_OPTIMIZER = "rlspl.optimizer.algorithm_owned"


def _p(
    parameter_id: str,
    owner: str,
    type_: ParameterType,
    default: object,
    minimum: int | float | None = None,
    maximum: int | float | None = None,
    *,
    tunable: bool = True,
    choices: tuple[object, ...] = (),
    description: str = "",
) -> ParameterDefinition:
    return ParameterDefinition(
        id=parameter_id,
        owner=owner,
        type=type_,
        default=default,
        minimum=minimum,
        maximum=maximum,
        tunable=tunable,
        choices=choices,
        description=description,
    )


def core_training_parameters() -> tuple[ParameterDefinition, ...]:
    owner = "core.training"
    return (
        _p("training.gamma", owner, ParameterType.FLOAT, 0.99, 0.0, 1.0),
        _p("training.seed", owner, ParameterType.INTEGER, 0, 0, tunable=False),
        _p("training.log_interval", owner, ParameterType.INTEGER, 10, 1, tunable=False),
    )


def build_initial_registry(
    plugin_roots: tuple[Path, ...] | list[Path] = (),
) -> ComponentRegistry:
    registry = ComponentRegistry()

    for descriptor in _environment_descriptors():
        registry.register_environment(descriptor)
    for descriptor in _algorithm_descriptors():
        registry.register_algorithm(descriptor)
    for descriptor in _behavior_descriptors():
        registry.register_behavior(descriptor)
    for descriptor in _optimizer_descriptors():
        registry.register_optimizer(descriptor)
    discover_plugins(registry, plugin_roots)
    return registry


def _environment_descriptors() -> tuple[EnvironmentDescriptor, ...]:
    return (
        EnvironmentDescriptor(
            id=MOUNTAIN_CAR,
            version="1.0.0",
            display_name="MountainCar (discrete)",
            description="Build momentum in a valley using three discrete engine commands.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.DISCRETE,
                observation_kind=ObservationKind.VECTOR,
                observation_dimensions=2,
                discrete_action_count=3,
                maximum_episode_steps=200,
                success_signal=True,
                success_definition=(
                    "An episode succeeds when it terminates with the car at or beyond "
                    "the environment's goal position (0.5 in MountainCar-v0)."
                ),
            ),
            dependencies={"gymnasium": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:MountainCar",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="mountain_car/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=CART_POLE,
            version="1.0.0",
            display_name="CartPole",
            description="Balance an upright pole by pushing its cart left or right.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.DISCRETE,
                observation_kind=ObservationKind.VECTOR,
                observation_dimensions=4,
                discrete_action_count=2,
                maximum_episode_steps=500,
                success_signal=True,
                success_definition=(
                    "An episode succeeds when the pole remains balanced for the full "
                    "500-step CartPole-v1 horizon."
                ),
            ),
            dependencies={"gymnasium": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:CartPole",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="cart_pole/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=ACROBOT,
            version="1.0.0",
            display_name="Acrobot",
            description="Swing a two-link underactuated system above its target height.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.DISCRETE,
                observation_kind=ObservationKind.VECTOR,
                observation_dimensions=6,
                discrete_action_count=3,
                maximum_episode_steps=500,
                success_signal=True,
                success_definition=(
                    "An episode succeeds when the environment terminates because the "
                    "free end has reached the target height."
                ),
            ),
            dependencies={"gymnasium": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:Acrobot",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="acrobot/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=LUNAR_LANDER_DISCRETE,
            version="1.0.0",
            display_name="LunarLander (discrete)",
            description="Land a spacecraft using four discrete engine commands.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.DISCRETE,
                observation_kind=ObservationKind.VECTOR,
                observation_dimensions=8,
                discrete_action_count=4,
                maximum_episode_steps=1000,
                success_signal=True,
                success_definition=(
                    "Studio marks a terminal landing episode successful when its return "
                    "is at least 200."
                ),
            ),
            dependencies={"gymnasium[box2d]": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:LunarLanderDiscrete",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="lunar_lander_discrete/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=MOUNTAIN_CAR_CONTINUOUS,
            version="1.0.0",
            display_name="MountainCar (continuous)",
            description="Build momentum with a continuously variable bounded engine force.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.CONTINUOUS,
                observation_kind=ObservationKind.VECTOR,
                action_bounded=True,
                observation_dimensions=2,
                maximum_episode_steps=999,
                success_signal=True,
                success_definition=(
                    "An episode succeeds when it terminates with the car at or beyond "
                    "the environment's goal position (0.45 in MountainCarContinuous-v0)."
                ),
            ),
            dependencies={"gymnasium": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:MountainCarContinuous",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="mountain_car_continuous/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=PENDULUM,
            version="1.0.0",
            display_name="Pendulum",
            description="Swing a pendulum upright using bounded continuous torque.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.CONTINUOUS,
                observation_kind=ObservationKind.VECTOR,
                action_bounded=True,
                observation_dimensions=3,
                maximum_episode_steps=200,
                success_signal=False,
                success_definition=None,
            ),
            dependencies={"gymnasium": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:Pendulum",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="pendulum/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=LUNAR_LANDER_CONTINUOUS,
            version="1.0.0",
            display_name="LunarLander (continuous)",
            description="Land a spacecraft using two continuously variable engine controls.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.CONTINUOUS,
                observation_kind=ObservationKind.VECTOR,
                action_bounded=True,
                observation_dimensions=8,
                maximum_episode_steps=1000,
                success_signal=True,
                success_definition=(
                    "Studio marks a terminal landing episode successful when its return "
                    "is at least 200."
                ),
            ),
            dependencies={"gymnasium[box2d]": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:LunarLanderContinuous",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="lunar_lander_continuous/environment.py.tmpl"
            ),
        ),
        EnvironmentDescriptor(
            id=BIPEDAL_WALKER,
            version="1.0.0",
            display_name="BipedalWalker",
            description="Coordinate four continuous joint motors to walk across terrain.",
            capabilities=EnvironmentCapabilities(
                action_kind=ActionKind.CONTINUOUS,
                observation_kind=ObservationKind.VECTOR,
                action_bounded=True,
                observation_dimensions=24,
                maximum_episode_steps=1600,
                success_signal=True,
                success_definition=(
                    "Studio marks an episode successful when its return reaches at least "
                    "300."
                ),
            ),
            dependencies={"gymnasium[box2d]": ">=0.29,<2"},
            entry_point="rlspl_runtime.environments:BipedalWalker",
            runtime_assets=EnvironmentRuntimeAssets(
                adapter_template="bipedal_walker/environment.py.tmpl"
            ),
        ),
    )


def _algorithm_descriptors() -> tuple[AlgorithmDescriptor, ...]:
    q_learning_parameters = (
        _p("q_learning.learning_rate", Q_LEARNING, ParameterType.FLOAT, 0.1, 1e-8, 1.0),
        _p("q_learning.bins_per_dimension", Q_LEARNING, ParameterType.INTEGER, 12, 2, 256),
    )
    dqn_parameters = (
        _p("dqn.learning_rate", DQN, ParameterType.FLOAT, 1e-3, 1e-8, 1.0),
        _p("dqn.hidden_dimension", DQN, ParameterType.INTEGER, 128, 8, 4096),
        _p("dqn.buffer_capacity", DQN, ParameterType.INTEGER, 100_000, 1),
        _p("dqn.batch_size", DQN, ParameterType.INTEGER, 64, 1),
        _p("dqn.target_update_frequency", DQN, ParameterType.INTEGER, 10, 1),
    )
    ddpg_parameters = (
        _p("ddpg.actor_learning_rate", DDPG, ParameterType.FLOAT, 1e-4, 1e-8, 1.0),
        _p("ddpg.critic_learning_rate", DDPG, ParameterType.FLOAT, 1e-3, 1e-8, 1.0),
        _p("ddpg.hidden_dimension", DDPG, ParameterType.INTEGER, 128, 8, 4096),
        _p("ddpg.buffer_capacity", DDPG, ParameterType.INTEGER, 1_000_000, 1),
        _p("ddpg.batch_size", DDPG, ParameterType.INTEGER, 64, 1),
        _p("ddpg.tau", DDPG, ParameterType.FLOAT, 1e-3, 1e-8, 1.0),
    )
    sac_parameters = (
        _p("sac.learning_rate", SAC, ParameterType.FLOAT, 3e-4, 1e-8, 1.0),
        _p("sac.hidden_dimension", SAC, ParameterType.INTEGER, 256, 8, 4096),
        _p("sac.buffer_capacity", SAC, ParameterType.INTEGER, 1_000_000, 1),
        _p("sac.batch_size", SAC, ParameterType.INTEGER, 256, 1),
        _p("sac.tau", SAC, ParameterType.FLOAT, 5e-3, 1e-8, 1.0),
        _p("sac.entropy_temperature", SAC, ParameterType.FLOAT, 0.2, 1e-8),
        _p(
            "sac.automatic_entropy_tuning",
            SAC,
            ParameterType.BOOLEAN,
            True,
            tunable=False,
        ),
    )

    vector = frozenset({ObservationKind.VECTOR})
    episodes_and_steps = frozenset({"episodes", "timesteps"})
    return (
        AlgorithmDescriptor(
            id=Q_LEARNING,
            version="1.2.0",
            display_name="Q-Learning",
            requirements=AlgorithmRequirements(
                action_kinds=frozenset({ActionKind.DISCRETE}),
                observation_kinds=frozenset({ObservationKind.DISCRETE, ObservationKind.VECTOR}),
                vector_observation_adapter="state_discretizer",
                supports_budget_units=frozenset({"episodes"}),
            ),
            composition=AlgorithmComposition(
                architecture_roles=("q_table", "state_discretizer"),
                exploration_role="selected behavior component",
                policy_interface=PolicyInterface.Q_VALUES,
                default_behavior_id=RANDOM_MIXTURE,
                optimizer_interface=OptimizerInterface.TABULAR_UPDATE,
                default_optimizer_id=DIRECT_UPDATE,
                evaluation_modes=frozenset({
                    EvaluationActionMode.DETERMINISTIC,
                    EvaluationActionMode.TRAINING_BEHAVIOR,
                }),
                checkpoint_roles=("q_table",),
            ),
            parameters=q_learning_parameters,
            dependencies={"numpy": ">=1.26,<3"},
            entry_point="rlspl_runtime.algorithms.q_learning:QLearningPlugin",
            verified_environment_ids=frozenset({MOUNTAIN_CAR}),
            runtime_assets=AlgorithmRuntimeAssets(
                agent_template="q_learning/agent.py.tmpl",
                trainer_template="q_learning/trainer.py.tmpl",
                checkpoint_filename="q-table.npz",
            ),
        ),
        AlgorithmDescriptor(
            id=DQN,
            version="1.2.0",
            display_name="DQN",
            requirements=AlgorithmRequirements(
                action_kinds=frozenset({ActionKind.DISCRETE}),
                observation_kinds=vector,
                supports_budget_units=episodes_and_steps,
            ),
            composition=AlgorithmComposition(
                architecture_roles=("q_network", "target_q_network"),
                optimizer_roles=("q_optimizer",),
                exploration_role="selected behavior component",
                policy_interface=PolicyInterface.Q_VALUES,
                perturbable_policy=True,
                default_behavior_id=RANDOM_MIXTURE,
                optimizer_interface=OptimizerInterface.TORCH_GRADIENT,
                default_optimizer_id=ADAM,
                evaluation_modes=frozenset({
                    EvaluationActionMode.DETERMINISTIC,
                    EvaluationActionMode.TRAINING_BEHAVIOR,
                }),
                memory_role="uniform_replay",
                target_update="hard",
                checkpoint_roles=("q_network", "target_q_network", "q_optimizer"),
            ),
            parameters=dqn_parameters,
            dependencies={"numpy": ">=1.26,<3", "torch": ">=2.2,<3"},
            entry_point="rlspl_runtime.algorithms.dqn:DQNPlugin",
            verified_environment_ids=frozenset({LUNAR_LANDER_DISCRETE, MOUNTAIN_CAR}),
            runtime_assets=AlgorithmRuntimeAssets(
                agent_template="dqn/agent.py.tmpl",
                trainer_template="dqn/trainer.py.tmpl",
                checkpoint_filename="dqn-checkpoint.pt",
            ),
        ),
        AlgorithmDescriptor(
            id=DDPG,
            version="1.2.0",
            display_name="DDPG",
            requirements=AlgorithmRequirements(
                action_kinds=frozenset({ActionKind.CONTINUOUS}),
                observation_kinds=vector,
                requires_bounded_actions=True,
                supports_budget_units=episodes_and_steps,
            ),
            composition=AlgorithmComposition(
                architecture_roles=("actor", "critic", "target_actor", "target_critic"),
                optimizer_roles=("actor_optimizer", "critic_optimizer"),
                exploration_role="selected behavior component",
                policy_interface=PolicyInterface.DETERMINISTIC_ACTOR,
                perturbable_policy=True,
                default_behavior_id=OU_NOISE,
                optimizer_interface=OptimizerInterface.TORCH_GRADIENT,
                default_optimizer_id=ADAM,
                evaluation_modes=frozenset({
                    EvaluationActionMode.DETERMINISTIC,
                    EvaluationActionMode.TRAINING_BEHAVIOR,
                }),
                memory_role="uniform_replay",
                target_update="soft",
                checkpoint_roles=("actor", "critic", "target_actor", "target_critic"),
            ),
            parameters=ddpg_parameters,
            dependencies={"numpy": ">=1.26,<3", "torch": ">=2.2,<3"},
            entry_point="rlspl_runtime.algorithms.ddpg:DDPGPlugin",
            verified_environment_ids=frozenset(),
            runtime_assets=AlgorithmRuntimeAssets(
                agent_template="ddpg/agent.py.tmpl",
                trainer_template="ddpg/trainer.py.tmpl",
                checkpoint_filename="ddpg-checkpoint.pt",
            ),
        ),
        AlgorithmDescriptor(
            id=SAC,
            version="1.2.0",
            display_name="SAC",
            requirements=AlgorithmRequirements(
                action_kinds=frozenset({ActionKind.CONTINUOUS}),
                observation_kinds=vector,
                requires_bounded_actions=True,
                supports_budget_units=episodes_and_steps,
            ),
            composition=AlgorithmComposition(
                architecture_roles=("stochastic_policy", "twin_critics", "target_twin_critics"),
                optimizer_roles=("policy_optimizer", "critic_optimizer"),
                exploration_role="selected behavior component",
                policy_interface=PolicyInterface.STOCHASTIC_POLICY,
                default_behavior_id=ENTROPY_SAMPLING,
                optimizer_interface=OptimizerInterface.TORCH_GRADIENT,
                default_optimizer_id=ADAM,
                evaluation_modes=frozenset({
                    EvaluationActionMode.DETERMINISTIC,
                    EvaluationActionMode.STOCHASTIC,
                    EvaluationActionMode.TRAINING_BEHAVIOR,
                }),
                memory_role="uniform_replay",
                target_update="soft",
                checkpoint_roles=("policy", "twin_critics", "target_twin_critics"),
                conditional_roles={
                    "alpha_optimizer": "sac.automatic_entropy_tuning == true",
                },
            ),
            parameters=sac_parameters,
            dependencies={"numpy": ">=1.26,<3", "torch": ">=2.2,<3"},
            entry_point="rlspl_runtime.algorithms.sac:SACPlugin",
            verified_environment_ids=frozenset(),
            runtime_assets=AlgorithmRuntimeAssets(
                agent_template="sac/agent.py.tmpl",
                trainer_template="sac/trainer.py.tmpl",
                checkpoint_filename="sac-checkpoint.pt",
            ),
        ),
    )


def _schedule_parameters(
    prefix: str,
    owner: str,
    *,
    start: float,
    end: float,
    decay: float = 0.995,
    quantity: str,
) -> tuple[ParameterDefinition, ...]:
    return (
        _p(
            f"{prefix}.{quantity}_start",
            owner,
            ParameterType.FLOAT,
            start,
            0.0,
            description=f"Initial {quantity.replace('_', ' ')} used by this behavior.",
        ),
        _p(
            f"{prefix}.{quantity}_end",
            owner,
            ParameterType.FLOAT,
            end,
            0.0,
            description=f"Lower endpoint for the {quantity.replace('_', ' ')} schedule.",
        ),
        _p(
            f"{prefix}.decay",
            owner,
            ParameterType.FLOAT,
            decay,
            0.0,
            1.0,
            description="Multiplicative factor used by the exponential schedule.",
        ),
        _p(
            f"{prefix}.schedule",
            owner,
            ParameterType.CATEGORICAL,
            "exponential",
            choices=("constant", "linear", "exponential"),
            description="How exploration intensity changes over the training budget.",
        ),
    )


def _behavior_descriptors() -> tuple[BehaviorDescriptor, ...]:
    discrete = frozenset({ActionKind.DISCRETE})
    continuous = frozenset({ActionKind.CONTINUOUS})
    both = frozenset({ActionKind.DISCRETE, ActionKind.CONTINUOUS})
    q_values = frozenset({PolicyInterface.Q_VALUES})
    deterministic_actor = frozenset({PolicyInterface.DETERMINISTIC_ACTOR})
    continuous_policy = frozenset({
        PolicyInterface.DETERMINISTIC_ACTOR,
        PolicyInterface.STOCHASTIC_POLICY,
    })
    return (
        BehaviorDescriptor(
            id=GREEDY,
            version="1.0.0",
            display_name="Greedy",
            description="Always choose a highest-valued discrete action, with random tie-breaking.",
            category="base decision",
            requirements=BehaviorRequirements(
                policy_interfaces=q_values,
                action_kinds=discrete,
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/greedy.py.tmpl"
            ),
            source_ids=("sutton_barto",),
        ),
        BehaviorDescriptor(
            id=RANDOM_MIXTURE,
            version="1.0.0",
            display_name="Random-action mixture",
            description=(
                "With a scheduled probability, replace the algorithm's base decision with "
                "a uniform action-space sample; this is epsilon-greedy for Q methods."
            ),
            category="action replacement",
            requirements=BehaviorRequirements(
                policy_interfaces=frozenset({
                    PolicyInterface.Q_VALUES,
                    PolicyInterface.DETERMINISTIC_ACTOR,
                    PolicyInterface.STOCHASTIC_POLICY,
                }),
                action_kinds=both,
            ),
            parameters=_schedule_parameters(
                "behavior.random_mixture", RANDOM_MIXTURE,
                start=1.0, end=0.05, quantity="probability",
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/random_mixture.py.tmpl"
            ),
            source_ids=("sutton_barto",),
        ),
        BehaviorDescriptor(
            id=BOLTZMANN,
            version="1.0.0",
            display_name="Boltzmann (softmax)",
            description="Sample discrete actions from a softmax distribution over Q-values.",
            category="score sampling",
            requirements=BehaviorRequirements(
                policy_interfaces=q_values,
                action_kinds=discrete,
            ),
            parameters=_schedule_parameters(
                "behavior.boltzmann", BOLTZMANN,
                start=1.0, end=0.1, quantity="temperature",
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/boltzmann.py.tmpl"
            ),
            source_ids=("sutton_barto",),
        ),
        BehaviorDescriptor(
            id=DETERMINISTIC,
            version="1.0.0",
            display_name="Deterministic actor",
            description="Use the continuous actor output directly, without external exploration noise.",
            category="base decision",
            requirements=BehaviorRequirements(
                policy_interfaces=deterministic_actor,
                action_kinds=continuous,
                requires_bounded_actions=True,
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/deterministic.py.tmpl"
            ),
            source_ids=("ddpg",),
        ),
        BehaviorDescriptor(
            id=GAUSSIAN_NOISE,
            version="1.0.0",
            display_name="Gaussian action noise",
            description="Add independent scheduled Gaussian noise to each bounded continuous action.",
            category="action noise",
            requirements=BehaviorRequirements(
                policy_interfaces=continuous_policy,
                action_kinds=continuous,
                requires_bounded_actions=True,
            ),
            parameters=_schedule_parameters(
                "behavior.gaussian", GAUSSIAN_NOISE,
                start=0.2, end=0.05, quantity="sigma",
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/gaussian_noise.py.tmpl"
            ),
            source_ids=("action_noise",),
        ),
        BehaviorDescriptor(
            id=OU_NOISE,
            version="1.0.0",
            display_name="Ornstein–Uhlenbeck action noise",
            description="Add temporally correlated noise to bounded continuous actions.",
            category="action noise",
            requirements=BehaviorRequirements(
                policy_interfaces=continuous_policy,
                action_kinds=continuous,
                requires_bounded_actions=True,
            ),
            parameters=(
                _p(
                    "behavior.ou.theta", OU_NOISE, ParameterType.FLOAT, 0.15, 0.0,
                    description="Mean-reversion strength of the OU process.",
                ),
                _p(
                    "behavior.ou.mu", OU_NOISE, ParameterType.FLOAT, 0.0,
                    description="Long-run mean of the OU process.",
                ),
                *_schedule_parameters(
                    "behavior.ou", OU_NOISE,
                    start=0.2, end=0.2, quantity="sigma",
                ),
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/ou_noise.py.tmpl"
            ),
            source_ids=("ddpg", "action_noise"),
        ),
        BehaviorDescriptor(
            id=PARAMETER_NOISE,
            version="1.0.0",
            display_name="Parameter-space noise",
            description="Perturb a copy of the policy model so exploration is consistent across a trajectory.",
            category="parameter noise",
            requirements=BehaviorRequirements(
                policy_interfaces=frozenset({
                    PolicyInterface.Q_VALUES,
                    PolicyInterface.DETERMINISTIC_ACTOR,
                }),
                action_kinds=both,
                requires_perturbable_policy=True,
            ),
            parameters=_schedule_parameters(
                "behavior.parameter_noise", PARAMETER_NOISE,
                start=0.1, end=0.01, quantity="sigma",
            ),
            dependencies={"torch": ">=2.2,<3"},
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/parameter_noise.py.tmpl"
            ),
            source_ids=("parameter_noise",),
        ),
        BehaviorDescriptor(
            id=ENTROPY_SAMPLING,
            version="1.0.0",
            display_name="Entropy-policy sampling",
            description="Sample directly from the stochastic policy learned by SAC.",
            category="policy sampling",
            requirements=BehaviorRequirements(
                policy_interfaces=frozenset({PolicyInterface.STOCHASTIC_POLICY}),
                action_kinds=continuous,
                requires_bounded_actions=True,
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/entropy_sampling.py.tmpl"
            ),
            source_ids=("sac",),
        ),
        BehaviorDescriptor(
            id=ALGORITHM_OWNED,
            version="1.0.0",
            display_name="Algorithm-owned behavior",
            description="Compatibility adapter for legacy algorithm plug-ins that own action selection.",
            category="legacy adapter",
            public=False,
            requirements=BehaviorRequirements(
                policy_interfaces=frozenset({PolicyInterface.ALGORITHM_OWNED}),
                action_kinds=both,
            ),
            runtime_assets=BehaviorRuntimeAssets(
                behavior_template="behavior/algorithm_owned.py.tmpl"
            ),
        ),
    )


def _optimizer_descriptors() -> tuple[OptimizerDescriptor, ...]:
    torch_gradient = frozenset({OptimizerInterface.TORCH_GRADIENT})
    return (
        OptimizerDescriptor(
            id=DIRECT_UPDATE,
            version="1.0.0",
            display_name="Direct tabular update",
            description=(
                "Apply the Q-Learning temporal-difference update directly to the selected "
                "Q-table cell; no gradient optimizer is involved."
            ),
            category="tabular update",
            requirements=OptimizerRequirements(
                interfaces=frozenset({OptimizerInterface.TABULAR_UPDATE})
            ),
            runtime_assets=OptimizerRuntimeAssets(
                optimizer_template="optimizer/direct_update.py.tmpl"
            ),
            source_ids=("sutton_barto",),
        ),
        OptimizerDescriptor(
            id=ADAM,
            version="1.0.0",
            display_name="Adam",
            description=(
                "Adaptive first- and second-moment gradient updates with bias correction."
            ),
            category="adaptive gradient",
            requirements=OptimizerRequirements(interfaces=torch_gradient),
            parameters=(
                _p(
                    "optimizer.adam.beta1", ADAM, ParameterType.FLOAT, 0.9, 0.0, 0.999999,
                    description="Exponential decay for the first-moment estimate.",
                ),
                _p(
                    "optimizer.adam.beta2", ADAM, ParameterType.FLOAT, 0.999, 0.0, 0.999999,
                    description="Exponential decay for the second-moment estimate.",
                ),
                _p(
                    "optimizer.adam.epsilon", ADAM, ParameterType.FLOAT, 1e-8, 1e-12,
                    description="Small denominator term used for numerical stability.",
                ),
                _p(
                    "optimizer.adam.weight_decay", ADAM, ParameterType.FLOAT, 0.0, 0.0,
                    description="L2-style weight-decay coefficient.",
                ),
                _p(
                    "optimizer.adam.amsgrad", ADAM, ParameterType.BOOLEAN, False,
                    tunable=False,
                    description="Use the AMSGrad maximum second-moment variant.",
                ),
            ),
            dependencies={"torch": ">=2.2,<3"},
            runtime_assets=OptimizerRuntimeAssets(
                optimizer_template="optimizer/adam.py.tmpl"
            ),
            source_ids=("adam",),
        ),
        OptimizerDescriptor(
            id=RMSPROP,
            version="1.0.0",
            display_name="RMSprop",
            description=(
                "Scale gradients by an exponential moving average of squared gradients."
            ),
            category="adaptive gradient",
            requirements=OptimizerRequirements(interfaces=torch_gradient),
            parameters=(
                _p(
                    "optimizer.rmsprop.alpha", RMSPROP, ParameterType.FLOAT, 0.99, 0.0, 0.999999,
                    description="Smoothing factor for the squared-gradient average.",
                ),
                _p(
                    "optimizer.rmsprop.epsilon", RMSPROP, ParameterType.FLOAT, 1e-8, 1e-12,
                    description="Small denominator term used for numerical stability.",
                ),
                _p(
                    "optimizer.rmsprop.momentum", RMSPROP, ParameterType.FLOAT, 0.0, 0.0, 0.999999,
                    description="Momentum coefficient applied to normalized updates.",
                ),
                _p(
                    "optimizer.rmsprop.weight_decay", RMSPROP, ParameterType.FLOAT, 0.0, 0.0,
                    description="L2-style weight-decay coefficient.",
                ),
                _p(
                    "optimizer.rmsprop.centered", RMSPROP, ParameterType.BOOLEAN, False,
                    tunable=False,
                    description="Normalize by an estimated variance instead of an uncentered moment.",
                ),
            ),
            dependencies={"torch": ">=2.2,<3"},
            runtime_assets=OptimizerRuntimeAssets(
                optimizer_template="optimizer/rmsprop.py.tmpl"
            ),
            source_ids=("rmsprop",),
        ),
        OptimizerDescriptor(
            id=SGD,
            version="1.0.0",
            display_name="SGD",
            description="Stochastic gradient descent with optional momentum and weight decay.",
            category="gradient descent",
            requirements=OptimizerRequirements(interfaces=torch_gradient),
            parameters=(
                _p(
                    "optimizer.sgd.momentum", SGD, ParameterType.FLOAT, 0.0, 0.0, 0.999999,
                    description="Fraction of the previous update accumulated as momentum.",
                ),
                _p(
                    "optimizer.sgd.weight_decay", SGD, ParameterType.FLOAT, 0.0, 0.0,
                    description="L2-style weight-decay coefficient.",
                ),
            ),
            dependencies={"torch": ">=2.2,<3"},
            runtime_assets=OptimizerRuntimeAssets(
                optimizer_template="optimizer/sgd.py.tmpl"
            ),
            source_ids=("sgd",),
        ),
        OptimizerDescriptor(
            id=ALGORITHM_OWNED_OPTIMIZER,
            version="1.0.0",
            display_name="Algorithm-owned optimizer",
            description=(
                "Compatibility adapter for legacy algorithm plug-ins that construct their "
                "own update rule."
            ),
            category="legacy adapter",
            public=False,
            requirements=OptimizerRequirements(
                interfaces=frozenset({OptimizerInterface.ALGORITHM_OWNED})
            ),
            runtime_assets=OptimizerRuntimeAssets(
                optimizer_template="optimizer/algorithm_owned.py.tmpl"
            ),
        ),
    )
