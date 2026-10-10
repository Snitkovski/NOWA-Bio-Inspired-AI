from agent_factory import AgentConfig, AgentFactory


def _spawn_agent():
    factory = AgentFactory(
        AgentConfig(
            actions=["eat", "sleep", "play"],
            hippocampus_capacity=64,
            cortex_capacity=64,
        )
    )
    return factory.spawn_default()


def test_agent_step_populates_fitness_histories_with_rolling_limit():
    agent = _spawn_agent()
    agent._fitness_history_limit = 3

    for _ in range(8):
        agent.step(
            context_events=["ctx"],
            reward=0.1,
            novelty=0.2,
            conflict=0.1,
        )

    assert isinstance(agent.affective_history, list)
    assert isinstance(agent.td_error_history, list)
    assert isinstance(agent.cortisol_history, list)
    assert 0 < len(agent.affective_history) <= 3
    assert 0 < len(agent.td_error_history) <= 3
    assert 0 < len(agent.cortisol_history) <= 3
    assert isinstance(agent.affective_history[-1], dict)
