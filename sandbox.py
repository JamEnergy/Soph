

m = MRU(3)

for i in range(0,5):
    m.insert(1+i,(1+i)*10)


for i in range(0,5):
    print (m.get(1+i))

m.insert(2, 20)
m.insert(5, 50)

m.insert(1, 10)
m.insert(1, 10)

pass