class ExperienceSample:
    """
    Один завершённый эпизод опыта
    """
    def __init__(self, context, action, reward):
        self.context = context      # list[str]
        self.action = action        # str
        self.reward = reward        # float
