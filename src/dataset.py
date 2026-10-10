class ExperienceDataset:
    """
    Последовательность жизненных эпизодов
    """
    def __init__(self, samples):
        self.samples = samples

    def __iter__(self):
        return iter(self.samples)

    def __len__(self):
        return len(self.samples)
