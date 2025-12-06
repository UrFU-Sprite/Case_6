from model import Model

model = Model()
print(model.send_query('как зайти в личный кабинет?').content)
