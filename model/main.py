from model import AdaptationModel


if __name__ == "__main__":
    empty_model = AdaptationModel()
    for i in range(30):
        empty_model.step()

