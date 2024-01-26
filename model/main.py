from model import AdaptationModel
from mesa.batchrunner import batch_run


if __name__ == "__main__":
    empty_model = AdaptationModel()

    empty_model.step()
