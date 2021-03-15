import pymongo
import os
import sys

import Settings
 
sys.path.insert(0, Settings.CONFIG_PATH)
import app_config
sys.path.pop(0)
do_implement=False
 
def main():
    db = pymongo.MongoClient()[app_config.db_name]
    print("MODULES:")  
    d=db.ctypes.find({},{'name':1})
    for row in d:
        print(row["name"]) 
        if do_implement:
            if row["name"]=="numbers":   
                query = { "name": row["name"] }
                newvalues = { "$set": { "isomorphicModule": "numbersreverse" } }
                db.ctypes.update_one(query, newvalues)  
            if row["name"]=="numbersreverse":   
                query = { "name": row["name"] }
                newvalues = { "$set": { "isomorphicModule": "numbers" } }
                db.ctypes.update_one(query, newvalues)  

    print("TASKS:")  
    d=db.ctasks.find({},{'taskid':1})
    for row in d:
        print(row["taskid"]) 
        if do_implement:          
            if row["taskid"]=="1":   
                query = { "taskid": row["taskid"] }
                newvalues = { "$set": { "isomorphicTask": "2" } }
                db.ctasks.update_one(query, newvalues)  
            if row["taskid"]=="2":   
                query = { "taskid": row["taskid"] }
                newvalues = { "$set": { "isomorphicTask": "1" } }
                db.ctasks.update_one(query, newvalues)  

if __name__ == "__main__":
    main()
