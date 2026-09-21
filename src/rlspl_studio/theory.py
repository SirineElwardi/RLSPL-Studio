"""Curated learning content for the RLSPL Studio browser interface.

This module is deliberately separate from descriptors and constraints.  Its data
can explain a choice, but it cannot enable, disable, validate, or generate one.
That boundary keeps pedagogical guidance from silently becoming product-line
semantics.
"""

from __future__ import annotations

from typing import Any

from .catalog import (
    ACROBOT,
    ADAM,
    BIPEDAL_WALKER,
    BOLTZMANN,
    CART_POLE,
    DDPG,
    DETERMINISTIC,
    DQN,
    DIRECT_UPDATE,
    ENTROPY_SAMPLING,
    GAUSSIAN_NOISE,
    GREEDY,
    LUNAR_LANDER_CONTINUOUS,
    LUNAR_LANDER_DISCRETE,
    MOUNTAIN_CAR,
    MOUNTAIN_CAR_CONTINUOUS,
    OU_NOISE,
    PARAMETER_NOISE,
    PENDULUM,
    Q_LEARNING,
    RANDOM_MIXTURE,
    RMSPROP,
    SAC,
    SGD,
    core_training_parameters,
)
from .descriptors import (
    AlgorithmDescriptor,
    BehaviorDescriptor,
    EnvironmentDescriptor,
    OptimizerDescriptor,
    ParameterDefinition,
)
from .registry import ComponentRegistry


ACADEMIC_SOURCES: dict[str, dict[str, str | int]] = {
    "sutton_barto": {
        "title": "Reinforcement Learning: An Introduction (2nd ed.)",
        "authors": "Sutton and Barto",
        "year": 2018,
        "url": "https://incompleteideas.net/book/the-book-2nd.html",
    },
    "watkins_dayan": {
        "title": "Q-learning",
        "authors": "Watkins and Dayan",
        "year": 1992,
        "url": "https://link.springer.com/article/10.1007/BF00992698",
    },
    "dqn": {
        "title": "Human-level control through deep reinforcement learning",
        "authors": "Mnih et al.",
        "year": 2015,
        "url": "https://www.nature.com/articles/nature14236",
    },
    "ddpg": {
        "title": "Continuous control with deep reinforcement learning",
        "authors": "Lillicrap et al.",
        "year": 2016,
        "url": "https://arxiv.org/abs/1509.02971",
    },
    "sac": {
        "title": "Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning",
        "authors": "Haarnoja et al.",
        "year": 2018,
        "url": "https://proceedings.mlr.press/v80/haarnoja18b.html",
    },
    "action_noise": {
        "title": "Action Noise in Off-Policy Deep Reinforcement Learning",
        "authors": "Hollenstein et al.",
        "year": 2022,
        "url": "https://arxiv.org/abs/2206.03787",
    },
    "parameter_noise": {
        "title": "Parameter Space Noise for Exploration",
        "authors": "Plappert et al.",
        "year": 2018,
        "url": "https://openreview.net/forum?id=ByBAl2eAZ",
    },
    "reward_shaping": {
        "title": "Policy Invariance Under Reward Transformations",
        "authors": "Ng, Harada, and Russell",
        "year": 1999,
        "url": "https://luthuli.cs.uiuc.edu/~daf/courses/Games/AIpapers/ml99-shaping.pdf",
    },
    "gym": {
        "title": "OpenAI Gym",
        "authors": "Brockman et al.",
        "year": 2016,
        "url": "https://arxiv.org/abs/1606.01540",
    },
    "cart_pole_control": {
        "title": "Neuronlike Adaptive Elements That Can Solve Difficult Learning Control Problems",
        "authors": "Barto, Sutton, and Anderson",
        "year": 1983,
        "url": "https://doi.org/10.1109/TSMC.1983.6313077",
    },
    "acrobot_coarse_coding": {
        "title": "Generalization in Reinforcement Learning: Successful Examples Using Sparse Coarse Coding",
        "authors": "Sutton",
        "year": 1996,
        "url": "https://proceedings.neurips.cc/paper/1995/hash/8f1d43620bc6bb580df6e80b0dc05c48-Abstract.html",
    },
    "mountain_car_thesis": {
        "title": "Efficient Memory-based Learning for Robot Control",
        "authors": "Moore",
        "year": 1990,
        "url": "https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-209.pdf",
    },
    "deep_rl_matters": {
        "title": "Deep Reinforcement Learning That Matters",
        "authors": "Henderson et al.",
        "year": 2018,
        "url": "https://doi.org/10.1609/aaai.v32i1.11694",
    },
    "rliable": {
        "title": "Deep Reinforcement Learning at the Edge of the Statistical Precipice",
        "authors": "Agarwal et al.",
        "year": 2021,
        "url": "https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html",
    },
    "random_search": {
        "title": "Random Search for Hyper-Parameter Optimization",
        "authors": "Bergstra and Bengio",
        "year": 2012,
        "url": "https://jmlr.org/papers/v13/bergstra12a.html",
    },
    "tpe": {
        "title": "Algorithms for Hyper-Parameter Optimization",
        "authors": "Bergstra et al.",
        "year": 2011,
        "url": "https://papers.nips.cc/paper/4443-algorithms-for-hyper-parameter-optimization",
    },
    "rlspl": {
        "title": "RLSPL: A software product line for streamlining reinforcement learning",
        "authors": "Wardi, Mzid, and Ziadi",
        "year": 2025,
        "url": "https://doi.org/10.1016/j.infsof.2025.107916",
    },
    "foda": {
        "title": "Feature-Oriented Domain Analysis (FODA) Feasibility Study",
        "authors": "Kang et al.",
        "year": 1990,
        "url": "https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=11231",
    },
    "feature_oriented_spl": {
        "title": "Feature-Oriented Software Product Lines: Concepts and Implementation",
        "authors": "Apel et al.",
        "year": 2013,
        "url": "https://doi.org/10.1007/978-3-642-37521-7",
    },
    "feature_model_analysis": {
        "title": "Automated Analysis of Feature Models 20 Years Later",
        "authors": "Benavides, Segura, and Ruiz-Cortes",
        "year": 2010,
        "url": "https://doi.org/10.1016/j.is.2009.01.001",
    },
    "adam": {
        "title": "Adam: A Method for Stochastic Optimization",
        "authors": "Kingma and Ba",
        "year": 2015,
        "url": "https://arxiv.org/abs/1412.6980",
    },
    "amsgrad": {
        "title": "On the Convergence of Adam and Beyond",
        "authors": "Reddi, Kale, and Kumar",
        "year": 2018,
        "url": "https://openreview.net/forum?id=ryQu7f-RZ",
    },
    "rmsprop": {
        "title": "Neural Networks for Machine Learning, Lecture 6e: rmsprop",
        "authors": "Tieleman and Hinton",
        "year": 2012,
        "url": "https://www.cs.toronto.edu/~tijmen/csc321/slides/lecture_slides_lec6.pdf",
    },
    "sgd": {
        "title": "Optimization Methods for Large-Scale Machine Learning",
        "authors": "Bottou, Curtis, and Nocedal",
        "year": 2018,
        "url": "https://doi.org/10.1137/16M1080173",
    },
}


ENVIRONMENT_THEORY: dict[str, dict[str, Any]] = {
    MOUNTAIN_CAR: {
        "visual": "mountain_car",
        "summary": "A car must build momentum in a valley before it can reach the flag.",
        "goal": "Reach the goal position on the right-hand hill before the time limit.",
        "observation": "A 2-value vector: horizontal position and velocity.",
        "actions": "Three discrete choices: push left, coast, or push right.",
        "native_reward": "The environment gives −1 for every step, so a shorter successful episode has a better return.",
        "episode_end": "The episode ends at the goal or is truncated after 200 steps.",
        "why_challenging": "Greedy movement toward the flag fails: the engine is too weak, so the agent must first move away to gain momentum.",
        "beginner_tip": "A flat return of −200 means the goal was not reached within the limit; it does not by itself prove that the code is broken.",
        "reward_shaping": {
            "status": "Theory only — the generated product keeps the native reward.",
            "idea": "A potential based on height or progress can make intermediate improvement visible.",
            "caution": "Arbitrary bonuses can change which policy is optimal. Potential-based shaping is the standard policy-invariance result.",
        },
        "sources": ["gym", "mountain_car_thesis", "sutton_barto", "reward_shaping"],
    },
    ACROBOT: {
        "visual": "acrobot",
        "summary": "Use one actuated joint to swing a two-link chain above a target height.",
        "goal": "Raise the free end of the outer link above the target while starting near the hanging-down state.",
        "observation": "A 6-value vector: sine and cosine of two joint angles plus their two angular velocities.",
        "actions": "Three discrete torque choices at the actuated joint: −1, 0, or +1.",
        "native_reward": "Every non-goal step gives −1; the step that reaches the target gives 0. Faster solutions therefore have a better return.",
        "episode_end": "The episode ends when the free end reaches the target or is truncated after 500 steps.",
        "why_challenging": "Only the middle joint is actuated, so the agent must exploit coupled dynamics and build energy rather than position both links directly.",
        "beginner_tip": "Compare this with MountainCar: both require deliberate momentum building, but Acrobot exposes a larger six-dimensional observation vector.",
        "reward_shaping": {
            "status": "Theory only — the generated product keeps the native step cost.",
            "idea": "A height-based potential can expose incremental swing progress before the terminal goal is reached.",
            "caution": "Direct height bonuses may favor hovering or change the intended shortest-time objective; policy-invariant potential shaping is safer.",
        },
        "sources": ["gym", "acrobot_coarse_coding", "sutton_barto", "reward_shaping"],
    },
    LUNAR_LANDER_DISCRETE: {
        "visual": "lunar_lander",
        "summary": "Control short engine bursts to land a spacecraft safely between the flags.",
        "goal": "Touch down upright and gently on the landing pad without crashing or leaving the play area.",
        "observation": "An 8-value vector describing position, velocity, angle, angular velocity, and two leg-contact indicators.",
        "actions": "Four discrete choices: do nothing, fire the left orientation engine, fire the main engine, or fire the right orientation engine.",
        "native_reward": "Shaped feedback reflects progress toward the pad, speed, tilt, leg contact, fuel use, and the final landing or crash outcome.",
        "episode_end": "The episode ends on landing, crash, or escape and can be truncated at 1,000 steps.",
        "why_challenging": "The agent must coordinate position, velocity, and attitude while delayed engine effects interact.",
        "beginner_tip": "Watch the trend across many seeds. A single smooth-looking landing or one high-return episode is weak evidence.",
        "reward_shaping": {
            "status": "Theory only — no reward transformation is selected here.",
            "idea": "LunarLander already exposes dense shaped feedback; extra shaping is usually unnecessary for a first experiment.",
            "caution": "Changing reward terms changes the task specification and makes results incomparable unless the transformation is recorded.",
        },
        "sources": ["gym", "sutton_barto", "deep_rl_matters"],
    },
    LUNAR_LANDER_CONTINUOUS: {
        "visual": "lunar_lander",
        "summary": "The landing task with continuously variable engine commands rather than four fixed actions.",
        "goal": "Touch down upright and gently on the landing pad without crashing or leaving the play area.",
        "observation": "An 8-value vector describing position, velocity, angle, angular velocity, and two leg-contact indicators.",
        "actions": "Two bounded continuous controls regulate the main and lateral engines.",
        "native_reward": "Shaped feedback reflects progress toward the pad, speed, tilt, leg contact, fuel use, and the final landing or crash outcome.",
        "episode_end": "The episode ends on landing, crash, or escape and can be truncated at 1,000 steps.",
        "why_challenging": "The policy must learn both which engine to use and the appropriate command magnitude.",
        "beginner_tip": "Continuous actions need an actor-style policy such as DDPG or SAC; DQN and tabular Q-Learning choose among discrete actions.",
        "reward_shaping": {
            "status": "Theory only — no reward transformation is selected here.",
            "idea": "The native task already supplies dense progress signals, making it suitable for studying continuous-control algorithms directly.",
            "caution": "If a reward transformation is introduced later, treat it as explicit variability with provenance rather than an invisible runtime tweak.",
        },
        "sources": ["gym", "ddpg", "sac"],
    },
    MOUNTAIN_CAR_CONTINUOUS: {
        "visual": "mountain_car_continuous",
        "summary": "The momentum-building valley task with a continuously variable engine force.",
        "goal": "Reach position 0.45 on the right-hand hill before the 999-step time limit.",
        "observation": "A 2-value vector: horizontal position and velocity.",
        "actions": "One bounded continuous force value between −1 and +1.",
        "native_reward": "Large actions incur a small quadratic energy penalty; reaching the goal adds +100.",
        "episode_end": "The episode terminates at the goal or is truncated after 999 steps.",
        "why_challenging": "The policy must learn both when to reverse direction for momentum and how much force is worth its control penalty.",
        "beginner_tip": "Pair this with DDPG or SAC, then compare it with discrete MountainCar to isolate how the action representation changes the product.",
        "reward_shaping": {
            "status": "Theory only — the generated product keeps Gymnasium's native reward.",
            "idea": "The native action penalty already expresses an efficiency preference in addition to task completion.",
            "caution": "Adding progress reward can make the result incomparable with the standard task and may discourage the necessary move away from the goal.",
        },
        "sources": ["gym", "mountain_car_thesis", "ddpg", "sac"],
    },
    PENDULUM: {
        "visual": "pendulum",
        "summary": "Apply continuous torque to swing a pendulum upright and keep it controlled.",
        "goal": "Minimize angle error, angular velocity, and control effort over the full episode.",
        "observation": "A 3-value vector: cosine of angle, sine of angle, and angular velocity.",
        "actions": "One bounded continuous torque value between −2 and +2.",
        "native_reward": "Reward is the negative weighted cost of angle error, angular velocity, and squared torque; zero is the theoretical maximum per step.",
        "episode_end": "There is no terminal success event; every episode is truncated after 200 steps.",
        "why_challenging": "The agent must first inject enough energy to swing upward, then switch to fine control without wasting torque.",
        "beginner_tip": "Pendulum is a return-only task in Studio: compare average reward and reward distributions, not success rate. Less-negative return is better.",
        "reward_shaping": {
            "status": "Theory only — the generated product keeps the native control cost.",
            "idea": "The native reward is already dense and decomposes the control objective into angle, velocity, and effort costs.",
            "caution": "Changing those weights changes what 'good control' means, so record any future reward variation as an explicit environment component.",
        },
        "sources": ["gym", "sutton_barto", "ddpg", "sac"],
    },
    BIPEDAL_WALKER: {
        "visual": "bipedal_walker",
        "summary": "Coordinate four motor commands so a two-legged body moves across uneven terrain.",
        "goal": "Travel forward without falling while using the leg motors efficiently.",
        "observation": "A 24-value vector containing hull motion, joint states, ground contacts, and lidar-like terrain measurements.",
        "actions": "Four bounded continuous motor commands control hip and knee joints.",
        "native_reward": "Forward progress is rewarded, motor effort is penalized, and falling receives a large penalty.",
        "episode_end": "The episode ends after a fall or task completion and can be truncated at 1,600 steps.",
        "why_challenging": "Many coupled continuous controls must produce stable, repeated movement; exploration can easily lead to falls.",
        "beginner_tip": "This is a harder and slower baseline than MountainCar. Compare across seeds and budget enough environment interaction.",
        "reward_shaping": {
            "status": "Theory only — the native walking reward remains active.",
            "idea": "Posture or gait bonuses may speed learning, but they also encode assumptions about what a desirable walk looks like.",
            "caution": "A shaped agent can optimize the proxy instead of the intended task; inspect behavior as well as aggregate return.",
        },
        "sources": ["gym", "sutton_barto", "deep_rl_matters"],
    },
    CART_POLE: {
        "visual": "cart_pole",
        "summary": "Balance a pole by moving the cart left or right.",
        "goal": "Keep the pole upright and the cart within the track limits for as long as possible.",
        "observation": "A 4-value vector: cart position, cart velocity, pole angle, and pole angular velocity.",
        "actions": "Two discrete choices apply force to the cart: left or right.",
        "native_reward": "The environment gives +1 for each step that the episode remains active.",
        "episode_end": "The episode ends when position or angle limits are crossed and can be truncated at 500 steps.",
        "why_challenging": "Small action effects accumulate quickly, so the policy must react to velocity as well as visible position and angle.",
        "beginner_tip": "CartPole is a compact built-in baseline. Q-Learning exposes discretization directly, while DQN learns values from the raw four-value vector.",
        "reward_shaping": {
            "status": "Theory only — the generated product keeps the native reward.",
            "idea": "Angle- or position-based feedback can be denser than survival reward.",
            "caution": "Extra shaping can reward staying near the center rather than simply solving the original balance task.",
        },
        "sources": ["gym", "cart_pole_control", "sutton_barto", "reward_shaping"],
    },
}


ALGORITHM_THEORY: dict[str, dict[str, Any]] = {
    Q_LEARNING: {
        "visual": "q_table",
        "summary": "A value-based, off-policy method that stores one estimated return for each discrete state–action pair.",
        "family": "Tabular value learning",
        "learns": "An action-value table Q(s,a); the policy chooses the action with the largest current value.",
        "exploration": "Exposes Q-values to a separate behavior component: greedy, random-action mixture (ε-greedy), or Boltzmann sampling.",
        "optimizer": "Uses a direct tabular temporal-difference update rather than a gradient optimizer.",
        "memory": "No replay buffer. Each transition updates the table directly.",
        "best_fit": "Small discrete action spaces and observations that are already discrete or can be discretized sensibly.",
        "trade_off": "Table size grows exponentially with discretized observation dimensions—the curse of dimensionality.",
        "beginner_tip": "Start here to see the RL update directly. More bins add detail but also create many more state cells to visit.",
        "equation": "Q(s,a) ← Q(s,a) + α[r + γ maxₐ′ Q(s′,a′) − Q(s,a)]",
        "equation_legend": "α is the learning rate, γ discounts future reward, and the bracketed term is the temporal-difference error.",
        "sources": ["watkins_dayan", "sutton_barto"],
    },
    DQN: {
        "visual": "dqn",
        "summary": "A neural network approximates action values, extending Q-learning to vector observations while retaining discrete actions.",
        "family": "Deep value learning",
        "learns": "An online Q-network; a delayed target network supplies more stable learning targets.",
        "exploration": "Exposes Q-values to greedy, random-action mixture, Boltzmann, or parameter-noise behavior components.",
        "optimizer": "Exposes differentiable PyTorch parameters; Adam is the default, while RMSprop and SGD are compatible alternatives.",
        "memory": "A replay buffer breaks short-term correlations by sampling past transitions in batches.",
        "best_fit": "Vector observations with a finite set of discrete actions.",
        "trade_off": "Neural approximation adds sensitivity to scale, learning rate, replay settings, seeds, and compute budget.",
        "beginner_tip": "The target network and replay buffer are stability mechanisms, not optional decorations around Q-learning.",
        "equation": "L(θ) = E[(r + γ maxₐ′ Q_target(s′,a′) − Qθ(s,a))²]",
        "equation_legend": "The online network θ is trained to reduce the squared gap between its value and a target computed with a delayed network.",
        "sources": ["dqn", "sutton_barto", "deep_rl_matters"],
    },
    DDPG: {
        "visual": "ddpg",
        "summary": "A deterministic actor chooses continuous actions while a critic estimates how valuable those actions are.",
        "family": "Off-policy deterministic actor–critic",
        "learns": "An actor μ(s), a critic Q(s,a), and slowly moving target copies of both networks.",
        "exploration": "Exposes a bounded deterministic actor to deterministic, random-action, Gaussian-noise, OU-noise, or parameter-noise behaviors.",
        "optimizer": "Actor and critic roles each receive an independent instance of the selected Adam, RMSprop, or SGD component.",
        "memory": "Transitions are reused from a replay buffer in random mini-batches.",
        "best_fit": "Bounded continuous action spaces where precise control magnitudes matter.",
        "trade_off": "DDPG can be brittle: critic error can mislead the actor, and exploration/noise scales matter.",
        "beginner_tip": "Actor and critic learning rates play different roles. Changing both at once makes failures harder to diagnose.",
        "equation": "a = μθ(s) + 𝒩; ∇θJ ≈ E[∇ₐQ(s,a)∇θμθ(s)]",
        "equation_legend": "The actor is improved through the critic's action gradient, while added noise 𝒩 supplies exploration.",
        "sources": ["ddpg", "sutton_barto", "deep_rl_matters"],
    },
    SAC: {
        "visual": "sac",
        "summary": "A stochastic actor–critic learns continuous control while explicitly rewarding useful policy entropy.",
        "family": "Off-policy maximum-entropy actor–critic",
        "learns": "A stochastic policy, two critics to reduce optimistic value estimates, and target critics.",
        "exploration": "Exposes stochastic and deterministic policy actions; compatible behaviors can sample the entropy policy or apply external random/Gaussian/OU action transforms.",
        "optimizer": "Policy, twin critics, and optional entropy temperature each receive an independent selected optimizer instance.",
        "memory": "Transitions are reused from a replay buffer in random mini-batches.",
        "best_fit": "Bounded continuous action spaces, especially when robust ongoing exploration is valuable.",
        "trade_off": "More networks and entropy tuning increase conceptual and computational complexity.",
        "beginner_tip": "Automatic entropy tuning adapts α; when enabled, the fixed temperature is an initial value rather than the whole exploration strategy.",
        "equation": "J(π) = E[Q(s,a) − α log π(a|s)]",
        "equation_legend": "The policy balances expected value Q with entropy; larger α places more weight on stochasticity.",
        "sources": ["sac", "sutton_barto", "deep_rl_matters"],
    },
}


def _parameter(
    label: str,
    summary: str,
    increase: str,
    decrease: str,
    interaction: str,
    *,
    sources: tuple[str, ...] = ("sutton_barto",),
) -> dict[str, Any]:
    return {
        "label": label,
        "summary": summary,
        "increase": increase,
        "decrease": decrease,
        "interaction": interaction,
        "sources": list(sources),
    }


PARAMETER_THEORY: dict[str, dict[str, Any]] = {
    "training.gamma": _parameter(
        "Discount factor (γ)",
        "Controls how strongly future rewards contribute to today's learning target.",
        "Looks further ahead but can propagate uncertainty over a longer horizon.",
        "Favors immediate reward and short-horizon behavior.",
        "Episode length and reward timing determine how noticeable γ is.",
    ),
    "training.seed": _parameter(
        "Training seed",
        "Initializes pseudorandom choices so an individual run can be reproduced.",
        "A different integer creates a different replication; it is not intrinsically better.",
        "A different integer creates a different replication; zero has no special learning meaning.",
        "Use several seeds to estimate variability instead of selecting a lucky run.",
        sources=("deep_rl_matters", "rliable"),
    ),
    "training.log_interval": _parameter(
        "Log interval",
        "Sets how often progress is written to the training log.",
        "Produces fewer log records and lower logging overhead.",
        "Provides finer monitoring detail but writes more often.",
        "This affects observability, not the intended learning rule.",
        sources=("rlspl",),
    ),
    "q_learning.learning_rate": _parameter(
        "Q-learning rate (α)",
        "Controls how much one temporal-difference update changes a table entry.",
        "Learns faster from recent evidence but may oscillate or overwrite useful estimates.",
        "Changes values smoothly but can require many more visits.",
        "Reward scale, discount factor, and state visitation all affect a useful range.",
        sources=("watkins_dayan", "sutton_barto"),
    ),
    "q_learning.epsilon_start": _parameter(
        "Initial exploration (ε start)",
        "Probability of a random action at the beginning of training.",
        "Collects broader early experience but sacrifices more immediate reward.",
        "Exploits initial estimates sooner and risks missing useful actions.",
        "Must be interpreted with ε end and ε decay as one schedule.",
    ),
    "q_learning.epsilon_end": _parameter(
        "Final exploration (ε end)",
        "Lower bound for the probability of a random action.",
        "Keeps testing alternatives late in training.",
        "Makes the final behavior greedier but less adaptive.",
        "It must not exceed ε start; decay controls how quickly it is reached.",
    ),
    "q_learning.epsilon_decay": _parameter(
        "Exploration decay",
        "Multiplier applied to ε after each scheduled decay step.",
        "Values closer to 1 preserve exploration for longer.",
        "Smaller values make the policy greedy sooner.",
        "Training budget determines how many times the multiplier is applied.",
    ),
    "q_learning.bins_per_dimension": _parameter(
        "Bins per observation dimension",
        "Discretizes each continuous observation coordinate before table lookup.",
        "Represents finer differences but multiplies table size and reduces visits per cell.",
        "Shares experience more broadly but can merge states that need different actions.",
        "For d dimensions and A actions, a uniform table has roughly binsᵈ × A values.",
    ),
    "dqn.learning_rate": _parameter(
        "Network learning rate",
        "Sets the optimizer step size for the online Q-network.",
        "Can reduce loss quickly but destabilize value estimates.",
        "Often improves stability but needs more updates.",
        "Batch size, reward scale, optimizer state, and target updates interact strongly.",
        sources=("dqn", "deep_rl_matters"),
    ),
    "dqn.hidden_dimension": _parameter(
        "Hidden-layer width",
        "Sets the number of units in the generated Q-network's hidden representation.",
        "Adds representational capacity, parameters, memory use, and compute cost.",
        "Runs faster but may underfit complex value functions.",
        "Capacity should be judged with observation complexity and available data.",
        sources=("dqn",),
    ),
    "dqn.buffer_capacity": _parameter(
        "Replay-buffer capacity",
        "Maximum number of past transitions retained for reuse.",
        "Preserves more diverse and older experience but uses more memory.",
        "Focuses on recent behavior but increases correlation and forgetting risk.",
        "Capacity must be at least the batch size.",
        sources=("dqn",),
    ),
    "dqn.batch_size": _parameter(
        "Replay batch size",
        "Number of stored transitions used in one gradient update.",
        "Produces smoother gradient estimates but uses more memory and compute per update.",
        "Makes cheaper, noisier updates.",
        "Cannot exceed replay capacity; learning rate often needs reconsideration when batch size changes.",
        sources=("dqn", "deep_rl_matters"),
    ),
    "dqn.target_update_frequency": _parameter(
        "Target update frequency",
        "Number of update intervals between hard copies from the online network to the target network.",
        "Keeps targets fixed longer, improving separation but making them staler.",
        "Tracks the online network more closely but weakens the stabilizing delay.",
        "Its meaning depends on how frequently the trainer performs optimization steps.",
        sources=("dqn",),
    ),
    "dqn.epsilon_start": _parameter(
        "Initial exploration (ε start)",
        "Probability of a random discrete action at the beginning of DQN training.",
        "Collects broader early replay data at the cost of short-term performance.",
        "Relies sooner on an initially inaccurate Q-network.",
        "Interpret together with ε end, ε decay, buffer fill, and budget.",
        sources=("dqn",),
    ),
    "dqn.epsilon_end": _parameter(
        "Final exploration (ε end)",
        "Minimum random-action probability retained by the ε-greedy policy.",
        "Maintains behavioral diversity later in training.",
        "Makes behavior closer to greedy evaluation.",
        "Must not exceed ε start; evaluation should normally use its own deterministic policy setting.",
        sources=("dqn",),
    ),
    "dqn.epsilon_decay": _parameter(
        "Exploration decay",
        "Controls how quickly DQN shifts from random actions toward its learned values.",
        "Values closer to 1 make the transition slower.",
        "Smaller values make the transition faster.",
        "A long training budget can turn a seemingly slow multiplicative decay into an early transition.",
        sources=("dqn",),
    ),
    "ddpg.actor_learning_rate": _parameter(
        "Actor learning rate",
        "Optimizer step size for the deterministic policy network.",
        "Lets the policy react faster to critic gradients but can amplify critic error.",
        "Makes policy change more cautiously.",
        "Judge it relative to the critic learning rate and target-update rate.",
        sources=("ddpg",),
    ),
    "ddpg.critic_learning_rate": _parameter(
        "Critic learning rate",
        "Optimizer step size for the action-value network.",
        "Fits new targets faster but can give the actor unstable guidance.",
        "Produces slower-moving value estimates.",
        "Reward scale, actor rate, batch size, and soft targets all interact.",
        sources=("ddpg",),
    ),
    "ddpg.hidden_dimension": _parameter(
        "Hidden-layer width",
        "Sets the generated actor and critic hidden representation size.",
        "Adds capacity and computational cost.",
        "Reduces cost but may underfit policy or value structure.",
        "Higher capacity needs enough diverse replay data to be useful.",
        sources=("ddpg",),
    ),
    "ddpg.buffer_capacity": _parameter(
        "Replay-buffer capacity",
        "Maximum number of continuous-control transitions retained.",
        "Increases experience diversity and memory usage.",
        "Prioritizes recent behavior but may lose rare useful transitions.",
        "Must be at least the batch size.",
        sources=("ddpg",),
    ),
    "ddpg.batch_size": _parameter(
        "Replay batch size",
        "Number of transitions used for each actor/critic update.",
        "Makes gradient estimates smoother but increases per-update cost.",
        "Makes cheaper and noisier updates.",
        "Capacity, learning rates, and update frequency jointly determine data reuse.",
        sources=("ddpg",),
    ),
    "ddpg.tau": _parameter(
        "Soft target rate (τ)",
        "Fraction of online-network weights blended into target networks at each update.",
        "Makes targets follow online networks faster and can reduce stability.",
        "Creates slower, smoother targets but more lag.",
        "Its effect accumulates over update frequency; τ is not an episode probability.",
        sources=("ddpg",),
    ),
    "ddpg.ou_theta": _parameter(
        "OU mean-reversion (θ)",
        "Controls how strongly temporally correlated exploration noise returns toward its mean.",
        "Pulls noise back faster and shortens sustained action deviations.",
        "Allows exploration noise to drift for longer.",
        "Interpret with OU σ and the environment's action scale.",
        sources=("ddpg",),
    ),
    "ddpg.ou_sigma": _parameter(
        "OU noise scale (σ)",
        "Controls the magnitude of DDPG's exploration perturbations.",
        "Explores actions more broadly but can produce disruptive control.",
        "Makes behavior steadier but risks insufficient exploration.",
        "Action bounds clip extreme commands; θ controls temporal persistence.",
        sources=("ddpg",),
    ),
    "sac.learning_rate": _parameter(
        "Network learning rate",
        "Optimizer step size used by SAC's policy and value networks.",
        "Adapts faster but may destabilize coupled actor, critics, and entropy updates.",
        "Changes networks more cautiously but requires more updates.",
        "Batch size, τ, reward scale, and entropy tuning all interact.",
        sources=("sac", "deep_rl_matters"),
    ),
    "sac.hidden_dimension": _parameter(
        "Hidden-layer width",
        "Sets the capacity of the generated policy and critic networks.",
        "Represents more complex functions at higher compute and memory cost.",
        "Reduces cost but may underfit.",
        "Larger networks need sufficient replay diversity and optimization budget.",
        sources=("sac",),
    ),
    "sac.buffer_capacity": _parameter(
        "Replay-buffer capacity",
        "Maximum number of transitions retained for off-policy updates.",
        "Keeps broader historical experience but consumes more memory.",
        "Emphasizes recent behavior and may forget rare experience.",
        "Must be at least the batch size.",
        sources=("sac",),
    ),
    "sac.batch_size": _parameter(
        "Replay batch size",
        "Number of transitions sampled per policy/critic update.",
        "Smooths updates but increases memory and compute per step.",
        "Makes cheaper, noisier updates.",
        "Learning rate and replay capacity influence the useful scale.",
        sources=("sac",),
    ),
    "sac.tau": _parameter(
        "Soft target rate (τ)",
        "Fraction of critic weights blended into target critics per update.",
        "Updates targets faster but can pass instability through sooner.",
        "Produces smoother but more delayed targets.",
        "The number of gradient updates determines the effective tracking speed.",
        sources=("sac",),
    ),
    "sac.entropy_temperature": _parameter(
        "Entropy temperature (α)",
        "Weights policy entropy relative to estimated return.",
        "Encourages more stochastic actions and broader exploration.",
        "Prioritizes exploitation and a more concentrated policy.",
        "With automatic tuning enabled, this value initializes a quantity that is then adapted.",
        sources=("sac",),
    ),
    "sac.automatic_entropy_tuning": _parameter(
        "Automatic entropy tuning",
        "Chooses whether SAC adapts entropy temperature toward a target entropy.",
        "True reduces manual α selection but introduces an additional optimization process.",
        "False keeps α fixed and makes exploration depend directly on the configured temperature.",
        "The entropy-temperature field has different operational meaning in the two modes.",
        sources=("sac",),
    ),
    "optimizer.adam.beta1": _parameter(
        "Adam first-moment decay (β₁)",
        "Controls how long Adam remembers the direction of recent gradients.",
        "Smooths the first moment over a longer history but reacts more slowly to a changed gradient direction.",
        "Tracks recent gradients more quickly but produces a noisier direction estimate.",
        "Interpret with the learning rate, β₂, and the nonstationary targets used by deep RL.",
        sources=("adam",),
    ),
    "optimizer.adam.beta2": _parameter(
        "Adam second-moment decay (β₂)",
        "Controls how long Adam remembers recent squared-gradient magnitudes.",
        "Makes the adaptive scale smoother but slower to react to changing gradient variance.",
        "Makes scaling more responsive and potentially more volatile.",
        "Very large β₂ values need enough optimization steps for reliable bias-corrected estimates.",
        sources=("adam",),
    ),
    "optimizer.adam.epsilon": _parameter(
        "Adam numerical epsilon (ε)",
        "Stabilizes division by the root second moment and also affects effective scaling when gradients are tiny.",
        "Reduces extreme normalization but can damp adaptive scaling.",
        "Preserves stronger adaptivity but approaches numerical sensitivity.",
        "This is optimizer epsilon, not the random-action probability used by ε-greedy behavior.",
        sources=("adam",),
    ),
    "optimizer.adam.weight_decay": _parameter(
        "Adam weight decay",
        "Penalizes large neural-network weights during gradient updates.",
        "Adds stronger regularization and can also suppress useful capacity.",
        "Approaches the unregularized optimization objective.",
        "Its effect depends on learning rate, network scale, and the optimizer implementation.",
        sources=("adam", "sgd"),
    ),
    "optimizer.adam.amsgrad": _parameter(
        "AMSGrad variant",
        "Chooses whether Adam retains a maximum second-moment estimate as proposed for improved convergence behavior.",
        "True activates AMSGrad; it can make denominators more conservative.",
        "False uses standard Adam.",
        "Treat this as an optimizer ablation and compare across several training seeds.",
        sources=("amsgrad",),
    ),
    "optimizer.rmsprop.alpha": _parameter(
        "RMSprop smoothing factor (ρ)",
        "Controls the memory of the moving average of squared gradients.",
        "Uses a longer, smoother history and adapts more slowly.",
        "Responds faster to new gradient scales but makes normalization noisier.",
        "Learning rate and gradient clipping determine the final update size too.",
        sources=("rmsprop",),
    ),
    "optimizer.rmsprop.epsilon": _parameter(
        "RMSprop numerical epsilon (ε)",
        "Stabilizes the denominator used to normalize gradients.",
        "Limits very large normalized updates but weakens adaptivity for small gradients.",
        "Makes normalization more sensitive when the squared-gradient average is near zero.",
        "This epsilon is unrelated to random-action exploration probability.",
        sources=("rmsprop",),
    ),
    "optimizer.rmsprop.momentum": _parameter(
        "RMSprop momentum",
        "Accumulates part of previous normalized updates.",
        "Can accelerate movement in consistent directions but may overshoot unstable targets.",
        "Makes each update depend more directly on the current normalized gradient.",
        "Tune jointly with learning rate and the squared-gradient smoothing factor.",
        sources=("rmsprop", "sgd"),
    ),
    "optimizer.rmsprop.weight_decay": _parameter(
        "RMSprop weight decay",
        "Adds an L2-style penalty to neural-network parameters.",
        "Regularizes weights more strongly but can underfit.",
        "Approaches the unregularized objective.",
        "Compare only with the same network and learning-rate conventions.",
        sources=("rmsprop", "sgd"),
    ),
    "optimizer.rmsprop.centered": _parameter(
        "Centered RMSprop",
        "Chooses whether normalization estimates gradient variance by subtracting the squared mean gradient.",
        "True adds a gradient-mean estimate and extra state.",
        "False uses the usual uncentered squared-gradient moment.",
        "The centered form costs more memory and is an empirical choice, not a compatibility requirement.",
        sources=("rmsprop",),
    ),
    "optimizer.sgd.momentum": _parameter(
        "SGD momentum",
        "Accumulates a velocity from earlier stochastic-gradient updates.",
        "Strengthens directional persistence and may accelerate or overshoot.",
        "Approaches plain stochastic gradient descent.",
        "Learning rate and momentum jointly set the effective dynamics.",
        sources=("sgd",),
    ),
    "optimizer.sgd.weight_decay": _parameter(
        "SGD weight decay",
        "Adds an L2-style penalty while SGD updates network parameters.",
        "Constrains weight magnitude more strongly and can reduce useful capacity.",
        "Approaches the unregularized objective.",
        "Its practical strength scales with the learning rate and update count.",
        sources=("sgd",),
    ),
}


UI_CONCEPTS: dict[str, dict[str, Any]] = {
    "monitoring_dashboard": {
        "title": "Reading the monitoring dashboard",
        "summary": "Monitoring observes execution evidence; it does not modify the selected product, seed, policy, or training process.",
        "details": [
            "Generated products appear before their first run; completed individual runs are read from the product's immutable artifacts.",
            "Study run status comes from the runner's atomically persisted state, not from browser guesses.",
            "The variability map compares resolved configurations, so it includes effective component defaults as well as explicitly selected axes.",
            "Replication seeds are execution metadata and remain separate from product variability.",
            "The raw reward line shows recorded episode returns; the rolling mean reduces short-term noise but can hide volatility.",
            "A rising training curve suggests learning progress, but evaluation across independent seeds is stronger evidence than one trace.",
            "Configuration comparison averages only completed replication seeds and never treats pending or failed runs as numeric zeros.",
            "Training reward is environment-specific: compare values only when reward definitions and evaluation protocols are compatible.",
            "Logs, configurations, versions, timestamps, and artifacts provide provenance for diagnosing unexpected results.",
        ],
        "sources": ["deep_rl_matters", "rliable", "sutton_barto", "rlspl"],
    },
    "budget_unit": {
        "title": "Budget unit",
        "summary": "Defines whether the training budget counts complete episodes or individual environment transitions.",
        "details": [
            "Episodes are intuitive but can contain different numbers of steps.",
            "Timesteps make interaction cost more directly comparable across runs.",
            "An algorithm descriptor decides which units it supports.",
        ],
        "sources": ["sutton_barto", "deep_rl_matters"],
    },
    "training_budget": {
        "title": "Training budget",
        "summary": "The maximum amount of environment interaction allocated to learning—not a promise of convergence.",
        "details": [
            "Larger budgets cost more time and can expose more learning progress.",
            "Compare algorithms under a clearly reported interaction budget.",
        ],
        "sources": ["deep_rl_matters"],
    },
    "checkpoint_policy": {
        "title": "Checkpoint policy",
        "summary": "Controls which learned parameters are saved while training runs.",
        "details": [
            "Best retains the strongest observed training checkpoint under the runtime's score rule.",
            "Periodic keeps snapshots at a fixed interval; disabled writes no training checkpoint.",
            "Checkpointing records artifacts; it does not define a feature branch in the RLSPL domain model.",
        ],
        "sources": ["rlspl"],
    },
    "hpo": {
        "title": "Hyperparameter search",
        "summary": "Runs several parameter trials to optimize one declared evaluation objective.",
        "details": [
            "A sampler proposes parameter values from tunable domains.",
            "Search differs from Explore: Explore preserves a comparison space; HPO tries to select a winner.",
            "The generated product executes either Random Search or Bayesian TPE locally; no external optimization service is required.",
            "Each proposal is scored across the declared trial seeds. The winner is then refitted and evaluated with the separate final-evaluation seeds.",
            "Trial outcomes are execution evidence; only the optional search capability and its declared choices belong to the product configuration.",
        ],
        "sources": ["random_search", "tpe", "deep_rl_matters", "rlspl"],
    },
    "sampler": {
        "title": "Search sampler",
        "summary": "The strategy used to propose values from tunable parameter domains.",
        "details": [
            "Random Search samples each declared domain independently and is a strong, transparent baseline.",
            "Bayesian TPE begins with random proposals, then uses completed trials to favor values that are denser among the better observations than among the rest.",
            "The sampler seed makes the proposal sequence reproducible; it is distinct from trial training seeds.",
        ],
        "sources": ["random_search", "tpe"],
    },
    "objective": {
        "title": "Search objective",
        "summary": "The single measured quantity that hyperparameter search tries to improve.",
        "details": ["It must also be collected by the evaluation protocol.", "Optimizing one metric can hide trade-offs in other metrics."],
        "sources": ["deep_rl_matters"],
    },
    "trials": {
        "title": "Search trials",
        "summary": "The number of parameter proposals evaluated by an HPO study.",
        "details": ["More trials cover more possibilities but multiply execution cost.", "Trial count and search seeds are different replication dimensions."],
        "sources": ["deep_rl_matters"],
    },
    "search_seeds": {
        "title": "Trial training seeds",
        "summary": "Every parameter proposal is trained independently with each declared search seed before receiving one aggregate score.",
        "details": [
            "Using several seeds reduces the chance that one lucky initialization wins the search.",
            "The approximate search workload is trials multiplied by trial seeds.",
            "Keep these seeds separate from final-evaluation seeds when you want a cleaner estimate of the selected configuration.",
        ],
        "sources": ["deep_rl_matters", "rliable"],
    },
    "aggregation": {
        "title": "Trial-score aggregation",
        "summary": "Combines the objective values from a proposal's trial seeds into the single value used for ranking.",
        "details": [
            "Mean uses every score but is sensitive to extremes.",
            "Median is robust but ignores the size of deviations.",
            "IQM averages the middle half when at least four scores exist; with fewer scores the runtime uses the mean.",
        ],
        "sources": ["rliable"],
    },
    "sampler_seed": {
        "title": "Sampler seed",
        "summary": "Controls only the reproducible sequence of proposed hyperparameter values.",
        "details": [
            "Changing it explores a different proposal sequence.",
            "It does not replace the trial training seeds that control stochastic learning runs.",
        ],
        "sources": ["random_search", "deep_rl_matters"],
    },
    "search_timeout": {
        "title": "Optional search timeout",
        "summary": "Stops proposing new trials after the wall-clock limit; a trial already in progress is allowed to finish.",
        "details": [
            "The trial count remains the deterministic upper bound when both settings are supplied.",
            "Wall-clock stopping can produce different completed-trial counts on different hardware.",
        ],
        "sources": ["deep_rl_matters"],
    },
    "hpo_top_k": {
        "title": "Top trials",
        "summary": "Controls how many leading completed trials are retained in the compact dashboard ranking.",
        "details": [
            "The complete append-only trial log remains available even when the dashboard shows only the leaders.",
            "This display choice does not change sampling, ranking, or the selected winner.",
        ],
        "sources": ["rlspl"],
    },
    "hpo_dashboard": {
        "title": "Reading the HPO dashboard",
        "summary": "The HPO view separates search evidence from the final agent so a promising trial is not confused with an independent evaluation result.",
        "details": [
            "Objective history plots each completed proposal and the best value observed so far.",
            "Per-seed scores expose whether a proposal is consistently good or won through one favorable run.",
            "Current best shows the fixed parameter values that will be materialized into the selected configuration.",
            "Final evaluation appears only after the winner has been refitted and measured with the configured final seeds.",
            "Failed trials remain counted and reported; they are not silently assigned an objective of zero.",
        ],
        "sources": ["tpe", "deep_rl_matters", "rliable"],
    },
    "evaluation": {
        "title": "Evaluation protocol",
        "summary": "A separate, declared procedure for measuring a trained agent across repeatable episodes and seeds.",
        "details": ["Training return describes learning experience; evaluation return measures the resulting policy.", "Multiple seeds expose run-to-run variability."],
        "sources": ["deep_rl_matters", "rliable"],
    },
    "metric.average_reward": {
        "title": "Average reward",
        "summary": "Arithmetic mean of episode returns. Easy to read, but sensitive to unusually high or low runs.",
        "details": ["Always interpret the sign and scale using the selected environment's reward definition."],
        "sources": ["sutton_barto", "rliable"],
    },
    "metric.cumulative_reward": {
        "title": "Cumulative reward",
        "summary": "Sum of rewards over an episode or declared measurement window; in episodic RL this is the return.",
        "details": ["Longer episodes can help or hurt this value depending on the environment's reward convention."],
        "sources": ["sutton_barto"],
    },
    "metric.success_rate": {
        "title": "Success rate",
        "summary": "Fraction of evaluation episodes that trigger the environment's explicit success signal.",
        "details": ["It is interpretable but discards differences between failures and between successes."],
        "sources": ["deep_rl_matters"],
    },
    "metric.reward_auc": {
        "title": "Reward AUC",
        "summary": "Area under a reward-versus-training curve, summarizing both learning speed and achieved performance.",
        "details": ["Comparisons require the same x-axis, budget, logging convention, and interpolation rule."],
        "sources": ["deep_rl_matters"],
    },
    "metric.training_time": {
        "title": "Training time",
        "summary": "Wall-clock duration of training, useful for operational cost but hardware- and load-dependent.",
        "details": ["Record platform metadata before treating timing differences as algorithmic evidence."],
        "sources": ["deep_rl_matters", "rlspl"],
    },
    "metric.environment_steps": {
        "title": "Environment steps",
        "summary": "Number of agent–environment transitions consumed; a direct measure of sample use.",
        "details": ["It does not measure neural-network computation performed per transition."],
        "sources": ["sutton_barto", "deep_rl_matters"],
    },
    "metric.episodes_to_threshold": {
        "title": "Episodes to threshold",
        "summary": "How many episodes are needed before a declared performance threshold is reached.",
        "details": ["Meaningful use requires the same threshold and smoothing rule for every configuration."],
        "sources": ["deep_rl_matters"],
    },
    "summaries": {
        "title": "Statistical summaries",
        "summary": "Describe the distribution across evaluation repetitions instead of reporting one run.",
        "details": ["Mean and median describe center; standard deviation describes spread; confidence intervals express estimator uncertainty; IQM is a robust aggregate over the middle 50%."],
        "sources": ["rliable", "deep_rl_matters"],
    },
    "visualizations": {
        "title": "Evaluation visualizations",
        "summary": "Learning curves show change over interaction, distributions show variability, and convergence views emphasize stabilization.",
        "details": ["Plots should display uncertainty or individual replications; a single smoothed curve can hide instability."],
        "sources": ["rliable", "deep_rl_matters"],
    },
    "exports": {
        "title": "Result exports",
        "summary": "JSON preserves structured metadata, CSV supports tabular analysis, and PNG captures rendered plots.",
        "details": ["Exports are artifacts of execution and do not alter the selected learning configuration."],
        "sources": ["rlspl"],
    },
}


EXPLORATION_GLOSSARY: dict[str, dict[str, str]] = {
    "explicit_selection": {
        "title": "Explicit selection",
        "definition": "A component or value included directly in the study, independently of the Configure workspace.",
        "example": "Environment ∈ {MountainCar, LunarLander} and Algorithm ∈ {Q-Learning, DQN}.",
    },
    "structural_axis": {
        "title": "Structural axis",
        "definition": "A finite list of alternative components or major configuration choices.",
        "example": "Environment ∈ {MountainCar, LunarLander}.",
    },
    "parameter_axis": {
        "title": "Parameter axis",
        "definition": "A finite list of explicit values substituted for one parameter.",
        "example": "Discount factor ∈ {0.95, 0.99}.",
    },
    "conditional_axis": {
        "title": "Conditional axis",
        "definition": "An axis applied only when its owning component is active.",
        "example": "ddpg.tau varies only in candidates whose algorithm is DDPG.",
    },
    "candidate": {
        "title": "Candidate",
        "definition": "One raw Cartesian combination of axis values before constraint resolution.",
        "example": "LunarLander continuous + DQN is still a candidate, even though its action contract is invalid.",
    },
    "valid_configuration": {
        "title": "Valid configuration",
        "definition": "A candidate accepted by every active model and constraint, with defaults resolved.",
        "example": "MountainCar + DQN with all required parameters materialized.",
    },
    "excluded_candidate": {
        "title": "Excluded candidate",
        "definition": "A candidate preserved in the manifest with the exact constraint issues that prevent generation.",
        "example": "A discrete-action algorithm paired with a continuous-action environment.",
    },
    "duplicate": {
        "title": "Equivalent candidate",
        "definition": "A different axis path that resolves to configuration content already represented once.",
        "example": "An inactive conditional parameter does not create a genuinely different product.",
    },
    "replication_seed": {
        "title": "Training replication seed",
        "definition": "A controlled random initialization used to repeat training for one configuration and expose run-to-run variability.",
        "example": "Training seeds 0, 1, and 2 create three independently trained agents for each valid configuration.",
    },
    "evaluation_seed": {
        "title": "Evaluation seed",
        "definition": "A random initialization used to evaluate an already trained policy; it changes evaluation episodes, not the learned parameters or number of training runs.",
        "example": "One trained agent evaluated with seeds 100 and 101 is tested on two reproducible episode sequences.",
        "beginner_tip": "One evaluation seed is executable, but multiple seeds are needed for dispersion and confidence summaries.",
    },
    "planned_run": {
        "title": "Planned run",
        "definition": "One valid unique configuration paired with one replication seed.",
        "example": "16 configurations × 3 seeds = 48 planned runs.",
    },
    "preview_limit": {
        "title": "Preview limit",
        "definition": "A safety bound on how many candidates are materialized in the browser preview; it is not a validity constraint.",
        "example": "A 10,000-candidate space can remain theoretically accepted while only its first 500 candidates are previewed.",
    },
    "frozen_manifest": {
        "title": "Frozen manifest",
        "definition": "A content-addressed, immutable record of the study definition, resolved variants, exclusions, and lineage.",
        "example": "The runner consumes the saved manifest rather than silently recomputing a changed UI state.",
    },
    "execution_state": {
        "title": "Execution state",
        "definition": "Runtime metadata such as status, timestamps, attempts, platform, and artifacts—not product variability.",
        "example": "Completed and failed are run outcomes, not selectable features.",
    },
}


ISSUE_EXPLANATIONS: dict[str, str] = {
    "CAP-01": "The algorithm cannot emit the kind of action accepted by the environment. Change either component; tuning parameters cannot repair this contract mismatch.",
    "CAP-02": "The algorithm cannot consume the environment's observation representation without a declared adapter.",
    "CAP-03": "This continuous-control algorithm requires finite action bounds so its outputs can be mapped safely to the environment.",
    "EVA-03": "Success-dependent metrics require a binary success signal. Return-only environments such as Pendulum should be compared with reward metrics unless an explicit success predicate is supplied.",
    "PAR-06": "A replay update cannot sample a batch larger than the number of transitions the buffer can hold.",
    "PAR-08": "A behavior intensity schedule must finish at or below its starting probability, temperature, or noise scale.",
    "BEH-01": "The selected action behavior is not installed in the component registry.",
    "BEH-02": "The behavior requires an action kind or policy interface that the selected environment-algorithm pair does not expose.",
    "BEH-03": "The requested evaluation action mode is not implemented by the selected algorithm interface.",
    "OPT-01": "The selected optimizer or update-rule component is not installed in the registry.",
    "OPT-02": "The optimizer contract does not match the selected algorithm: tabular direct updates and neural-network gradient updates are different interfaces.",
    "HPO-01": "Search and tunable bindings must appear together: an HPO product needs at least one declared search domain, and a tunable domain needs an enabled search.",
    "HPO-02": "The chosen search strategy has no registered runtime provider.",
    "HPO-05": "The objective must be emitted by evaluation; reward AUC additionally requires reward-trace collection.",
    "RES-01": "This is a scale warning, not an invalidity result. Dense Q-table size grows exponentially with observation dimensions.",
    "ADV-01": "The capability contracts match, but this exact pair has not been marked as a verified baseline. It remains valid and generatable.",
    "ADV-06": "The configuration remains valid, but trials multiplied by trial seeds creates a large number of training runs before the final fit.",
    "MON-05": "The selected run is a normal product execution and therefore has no HPO trial evidence.",
    "EXP-03": "Only the preview is truncated. Increase the limit to materialize the full accepted design space before saving an executable manifest.",
}


def _generic_environment_theory(descriptor: EnvironmentDescriptor) -> dict[str, Any]:
    capabilities = descriptor.capabilities
    dimensions = (
        f"{capabilities.observation_dimensions}-value "
        if capabilities.observation_dimensions is not None
        else ""
    )
    if capabilities.action_kind.value == "discrete":
        count = capabilities.discrete_action_count
        actions = f"{count} discrete actions." if count else "A finite set of discrete actions."
    else:
        bounded = "bounded " if capabilities.action_bounded else ""
        actions = f"A {bounded}continuous action space."
    return {
        "visual": "generic_environment",
        "summary": descriptor.description or "An externally supplied reinforcement-learning environment.",
        "goal": "Consult the component documentation for its task objective and success definition.",
        "observation": f"A {dimensions}{capabilities.observation_kind.value} observation contract.",
        "actions": actions,
        "native_reward": "The plug-in owns the native reward definition; inspect its documentation before interpreting returns.",
        "episode_end": (
            f"The declared limit is {capabilities.maximum_episode_steps} steps."
            if capabilities.maximum_episode_steps
            else "Termination and truncation are defined by the plug-in."
        ),
        "why_challenging": "Difficulty depends on the plug-in's dynamics, reward signal, and observation/action geometry.",
        "beginner_tip": "A plug-in is selected through the same capability contract as a built-in component; its origin is not a quality grade.",
        "reward_shaping": {
            "status": "Theory only — reward behavior is owned by the plug-in.",
            "idea": "Document any future reward transformation as explicit variability.",
            "caution": "Never infer the meaning of a numeric return without the plug-in's reward specification.",
        },
        "sources": ["sutton_barto", "reward_shaping", "rlspl"],
    }


def _generic_algorithm_theory(descriptor: AlgorithmDescriptor) -> dict[str, Any]:
    composition = descriptor.composition
    return {
        "visual": "generic_algorithm",
        "summary": descriptor.description or "An externally supplied reinforcement-learning algorithm.",
        "family": "Plug-in algorithm",
        "learns": f"Declared architecture roles: {', '.join(composition.architecture_roles)}.",
        "exploration": (
            f"Exposes the {composition.policy_interface.value} decision interface; "
            f"default behavior: {composition.default_behavior_id or 'algorithm-owned'}."
        ),
        "optimizer": (
            f"Exposes the {composition.optimizer_interface.value} update interface; "
            f"default optimizer: {composition.default_optimizer_id or 'algorithm-owned'}."
        ),
        "memory": (
            f"Declared memory role: {composition.memory_role}."
            if composition.memory_role
            else "No replay-memory role is declared."
        ),
        "best_fit": "Environments satisfying the plug-in's action, observation, and action-bound contracts.",
        "trade_off": "Consult the plug-in's own evidence for convergence behavior, resource cost, and sensitivity.",
        "beginner_tip": "Capability compatibility proves composability, not empirical superiority.",
        "equation": "Component-provided learning rule",
        "equation_legend": "The plug-in should document its update objective and assumptions.",
        "sources": ["sutton_barto", "rlspl"],
    }


def _generic_parameter_theory(definition: ParameterDefinition) -> dict[str, Any]:
    if definition.id.startswith("behavior."):
        source = (
            "parameter_noise"
            if "parameter_noise" in definition.id
            else "action_noise"
            if ".gaussian." in definition.id or ".ou." in definition.id
            else "sutton_barto"
        )
        if definition.id.endswith(".schedule"):
            return _parameter(
                definition.id,
                definition.description,
                "Choose linear or exponential to reduce intensity over time; constant preserves the start value.",
                "This is a categorical mechanism, so it has no numerical decrease direction.",
                "The start, end, decay, and training budget determine the realized trajectory.",
                sources=(source,),
            )
        if definition.id.endswith(".decay"):
            return _parameter(
                definition.id,
                definition.description,
                "Values closer to one retain exploration intensity for longer under exponential decay.",
                "Smaller values move toward the configured endpoint sooner.",
                "It is inactive for constant or linear schedules and depends on the training budget.",
                sources=(source,),
            )
        if definition.id.endswith("_start"):
            return _parameter(
                definition.id,
                definition.description,
                "Begins training with stronger randomization, temperature, or perturbation.",
                "Begins closer to the algorithm's base decision.",
                "The selected behavior defines the units; compare with its endpoint and schedule.",
                sources=(source,),
            )
        if definition.id.endswith("_end"):
            return _parameter(
                definition.id,
                definition.description,
                "Retains stronger exploration late in training.",
                "Ends closer to deterministic exploitation or lower-temperature sampling.",
                "The endpoint cannot exceed the start value in the current decreasing schedules.",
                sources=(source,),
            )
        if definition.id == "behavior.ou.theta":
            return _parameter(
                "OU mean reversion (θ)", definition.description,
                "Returns correlated noise toward its mean more quickly.",
                "Lets deviations persist for longer.",
                "Interpret with σ, μ, action bounds, and episode length.",
                sources=("ddpg", "action_noise"),
            )
        if definition.id == "behavior.ou.mu":
            return _parameter(
                "OU long-run mean (μ)", definition.description,
                "Shifts the correlated-noise process toward a more positive perturbation.",
                "Shifts it toward a more negative perturbation.",
                "Zero is the usual unbiased-noise setting; action clipping can still create asymmetry.",
                sources=("ddpg", "action_noise"),
            )
    bounds = []
    if definition.minimum is not None:
        bounds.append(f"minimum {definition.minimum}")
    if definition.maximum is not None:
        bounds.append(f"maximum {definition.maximum}")
    boundary = f" Declared range: {', '.join(bounds)}." if bounds else ""
    return _parameter(
        definition.id,
        (definition.description or "A parameter declared by an external component.") + boundary,
        "The direction of effect must be documented by the component author.",
        "The direction of effect must be documented by the component author.",
        f"This setting is active only while {definition.owner} owns the selected component.",
        sources=("rlspl",),
    )


BEHAVIOR_THEORY: dict[str, dict[str, Any]] = {
    GREEDY: {
        "summary": "Exploit current Q estimates with no deliberate random exploration.",
        "mechanism": "Choose an action with maximal Q(s,a); ties may be broken randomly.",
        "best_fit": "A learned Q-function, especially for evaluation or an exploitation baseline.",
        "trade_off": "Simple and stable, but it can lock onto early mistakes during training.",
        "equation": "a = arg max_a Q(s,a)",
        "sources": ["sutton_barto"],
    },
    RANDOM_MIXTURE: {
        "summary": "Mix the algorithm's base decision with uniform random actions.",
        "mechanism": "Use a random action with probability ε and the base policy otherwise; ε follows the selected schedule.",
        "best_fit": "Discrete Q methods (the familiar ε-greedy case) and sampleable continuous action spaces.",
        "trade_off": "Broad coverage is easy to understand, but random continuous actions may be physically abrupt.",
        "equation": "π_b = (1−ε)π_base + εU(A)",
        "sources": ["sutton_barto"],
    },
    BOLTZMANN: {
        "summary": "Turn Q-values into a distribution instead of discarding their relative magnitudes.",
        "mechanism": "Sample action a with probability proportional to exp(Q(s,a)/T).",
        "best_fit": "Discrete algorithms that expose a complete vector of action scores.",
        "trade_off": "Temperature is interpretable, but sensitivity to Q-value scale can make it hard to tune.",
        "equation": "P(a|s) = exp(Q(s,a)/T) / Σ_b exp(Q(s,b)/T)",
        "sources": ["sutton_barto"],
    },
    DETERMINISTIC: {
        "summary": "Use the actor's bounded action directly, without an external exploration transform.",
        "mechanism": "The behavior delegates every choice to μ(s).",
        "best_fit": "A deterministic actor baseline or noise-free ablation.",
        "trade_off": "Valid and useful for comparison, but usually weak as the only source of training exploration.",
        "equation": "a = μ(s)",
        "sources": ["ddpg"],
    },
    GAUSSIAN_NOISE: {
        "summary": "Perturb each continuous action with independent Gaussian noise and clip to bounds.",
        "mechanism": "Add scheduled zero-mean noise scaled to the action range.",
        "best_fit": "Bounded continuous-control policies where uncorrelated perturbations are desired.",
        "trade_off": "Easy to tune, but successive actions are not temporally correlated.",
        "equation": "a = clip(a_base + σξ), ξ ~ N(0,I)",
        "sources": ["action_noise"],
    },
    OU_NOISE: {
        "summary": "Apply temporally correlated, mean-reverting noise to continuous actions.",
        "mechanism": "Maintain an OU state across a trajectory and reset it between episodes.",
        "best_fit": "Bounded continuous actions when smooth correlated exploration is a useful hypothesis.",
        "trade_off": "Correlation is not universally better; compare it empirically with Gaussian noise.",
        "equation": "xₜ₊₁ = xₜ + θ(μ−xₜ) + σξₜ",
        "sources": ["ddpg", "action_noise"],
    },
    PARAMETER_NOISE: {
        "summary": "Perturb policy weights once per episode so action changes remain state-dependent and coherent.",
        "mechanism": "Act with a noisy copy of the Q-network or deterministic actor while learning updates the original model.",
        "best_fit": "DQN and DDPG, whose generated neural policy models expose a perturbation interface.",
        "trade_off": "Trajectory-level consistency costs an extra model copy and depends on parameter scale.",
        "equation": "θ̃ = θ + σξ; a ~ π_{θ̃}(·|s)",
        "sources": ["parameter_noise"],
    },
    ENTROPY_SAMPLING: {
        "summary": "Sample from SAC's learned stochastic policy rather than adding a separate noise process.",
        "mechanism": "The policy supplies exploration; SAC's entropy temperature remains algorithm-owned because it changes the learning objective.",
        "best_fit": "Algorithms exposing a stochastic-policy sampling interface.",
        "trade_off": "Exploration is learned and state-dependent, but depends strongly on entropy optimization.",
        "equation": "a ~ π_φ(·|s)",
        "sources": ["sac"],
    },
}


def _generic_behavior_theory(descriptor: BehaviorDescriptor) -> dict[str, Any]:
    return {
        "summary": descriptor.description,
        "mechanism": f"Component category: {descriptor.category}.",
        "best_fit": "Algorithms and environments satisfying the declared behavior capability contract.",
        "trade_off": "Capability compatibility guarantees composition, not empirical superiority.",
        "equation": "Component-defined action transformation",
        "sources": list(descriptor.source_ids or ("rlspl",)),
    }


OPTIMIZER_THEORY: dict[str, dict[str, Any]] = {
    DIRECT_UPDATE: {
        "summary": "Q-Learning changes one table entry directly from a temporal-difference error.",
        "mechanism": "No gradient optimizer is constructed; the learning-rate scalar multiplies the TD error in the tabular update.",
        "best_fit": "Algorithms exposing the tabular-update interface, currently Q-Learning.",
        "trade_off": "Transparent and inexpensive, but it does not update differentiable function approximators.",
        "equation": "Q(s,a) ← Q(s,a) + α[r + γ max Q(s′,·) − Q(s,a)]",
        "sources": ["watkins_dayan", "sutton_barto"],
    },
    ADAM: {
        "summary": "Adapt each parameter using bias-corrected first and second gradient moments.",
        "mechanism": "Maintain exponential moving averages of gradients and squared gradients, then normalize the update coordinate-wise.",
        "best_fit": "A strong default for DQN, DDPG, and SAC when gradient scales differ across parameters.",
        "trade_off": "Often needs less initial tuning than SGD, but beta, epsilon, weight decay, and learning rate still affect stability and generalization.",
        "equation": "θₜ ← θₜ₋₁ − α m̂ₜ/(√v̂ₜ + ε)",
        "sources": ["adam", "amsgrad"],
    },
    RMSPROP: {
        "summary": "Normalize each gradient by a moving average of recent squared gradients.",
        "mechanism": "Accumulate an exponentially weighted squared-gradient statistic and divide the update by its root mean square.",
        "best_fit": "Deep value or actor-critic experiments where per-parameter adaptive scaling is useful.",
        "trade_off": "The smoothing factor, epsilon, and optional momentum add sensitivity; it has no Adam-style first-moment bias correction.",
        "equation": "vₜ ← ρvₜ₋₁ + (1−ρ)gₜ²; θₜ ← θₜ₋₁ − αgₜ/(√vₜ+ε)",
        "sources": ["rmsprop"],
    },
    SGD: {
        "summary": "Move parameters against the stochastic gradient, optionally accumulating momentum.",
        "mechanism": "Use one shared learning-rate scale; momentum carries part of earlier updates into the current step.",
        "best_fit": "Controlled optimizer comparisons and cases where a simple, non-adaptive update is desired.",
        "trade_off": "Conceptually direct and memory-efficient, but usually requires more careful learning-rate and momentum tuning in deep RL.",
        "equation": "θₜ ← θₜ₋₁ − αgₜ",
        "sources": ["sgd"],
    },
}


def _generic_optimizer_theory(descriptor: OptimizerDescriptor) -> dict[str, Any]:
    return {
        "summary": descriptor.description,
        "mechanism": f"Component category: {descriptor.category}.",
        "best_fit": "Algorithms satisfying the declared parameter-update interface.",
        "trade_off": "Contract compatibility guarantees composition, not learning performance.",
        "equation": "Component-defined parameter update",
        "sources": list(descriptor.source_ids or ("rlspl",)),
    }


def theory_catalog(registry: ComponentRegistry) -> dict[str, Any]:
    """Build JSON-safe educational metadata for every currently registered item."""

    referenced_behaviors = {
        item.composition.default_behavior_id
        for item in registry.algorithms
        if item.composition.default_behavior_id
    }
    referenced_optimizers = {
        item.composition.default_optimizer_id
        for item in registry.algorithms
        if item.composition.default_optimizer_id
    }

    environments = {
        descriptor.id: dict(
            ENVIRONMENT_THEORY.get(descriptor.id)
            or _generic_environment_theory(descriptor)
        )
        for descriptor in registry.environments
    }
    algorithms = {
        descriptor.id: dict(
            ALGORITHM_THEORY.get(descriptor.id)
            or _generic_algorithm_theory(descriptor)
        )
        for descriptor in registry.algorithms
    }
    behaviors = {
        descriptor.id: dict(
            BEHAVIOR_THEORY.get(descriptor.id)
            or _generic_behavior_theory(descriptor)
        )
        for descriptor in registry.behaviors
        if descriptor.public or descriptor.id in referenced_behaviors
    }
    optimizers = {
        descriptor.id: dict(
            OPTIMIZER_THEORY.get(descriptor.id)
            or _generic_optimizer_theory(descriptor)
        )
        for descriptor in registry.optimizers
        if descriptor.public or descriptor.id in referenced_optimizers
    }
    definitions: list[ParameterDefinition] = list(core_training_parameters())
    for environment in registry.environments:
        definitions.extend(environment.parameters)
    for algorithm in registry.algorithms:
        definitions.extend(algorithm.parameters)
    for behavior in registry.behaviors:
        definitions.extend(behavior.parameters)
    for optimizer in registry.optimizers:
        definitions.extend(optimizer.parameters)
    parameters = {
        definition.id: dict(
            PARAMETER_THEORY.get(definition.id)
            or _generic_parameter_theory(definition)
        )
        for definition in definitions
    }
    return {
        "schema_version": "1.0",
        "notice": "Educational guidance only. This content never changes validity or generated runtime behavior.",
        "environments": environments,
        "algorithms": algorithms,
        "behaviors": behaviors,
        "optimizers": optimizers,
        "parameters": parameters,
        "concepts": UI_CONCEPTS,
        "exploration_glossary": EXPLORATION_GLOSSARY,
        "issue_explanations": ISSUE_EXPLANATIONS,
        "sources": ACADEMIC_SOURCES,
    }
