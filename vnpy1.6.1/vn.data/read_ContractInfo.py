import shelve
import pandas as pd

f = shelve.open(os.path.join('/home/william/Documents/myCTP/vnpy1.6.1/vn.data/ContractInfo',("20170606_"+contractFileName)))

contractInfoHeader = ["InstrumentID", "InstrumentName", "ProductClass",\
                      "ExchangeID", "VolumeMultiple", "PriceTick"]    
contractInfoData = []   

for key, value in f['data'].items():
    data = [value.symbol, value.name, value.productClass, value.exchange,\
            value.size, value.priceTick]
    #print data
    contractInfoData.append(data)   
f.close()
#print contractInfoData
contractInfo = pd.DataFrame(contractInfoData, columns = contractInfoHeader)
print contractInfo
