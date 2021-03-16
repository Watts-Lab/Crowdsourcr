import pymongo
import os
import sys

import Settings
 
sys.path.insert(0, Settings.CONFIG_PATH)
import app_config
sys.path.pop(0)
config_filename="config_jared.json.production"
do_implement=False
 

def mapIsoName(name):
    frags=name.split('_')
    if frags[-1]=="dem":
        frags[-1]="rep"
        return "_".join(frags)
    else:
        if frags[-1]=="rep":
            frags[-1]="dem"
            return "_".join(frags)
        else:
            return None



def main():
    app_config.populate_config(config_filename)
    db = pymongo.MongoClient()[app_config.db_name]
    print("MODULES:")  
    d=db.ctypes.find({},{'name':1})
    for row in d:
        isoName=mapIsoName(row["name"])
        if isoName!=None:
            query = { "name": row["name"] }
            newvalues = { "$set": { "isomorphicModule": isoName } }
            if do_implement:
                db.ctypes.update_one(query, newvalues)  
            print("setting isomorphicModule of module "+row["name"]+" to "+isoName)
        else:
            query = { "name": row["name"] }
            newvalues = { "$set": { "isomorphicModule": None } }
            if do_implement:
                db.ctypes.update_one(query, newvalues)  
            print("skipping module "+row["name"])

    print("TASKS:")  
    d=db.ctasks.find({},{'taskid':1})
    for row in d:
        isoName=mapIsoName(row["taskid"])
        if isoName!=None:
            query = { "taskid": row["taskid"] }
            newvalues = { "$set": { "isomorphicTask": isoName } }
            if do_implement:
                db.ctasks.update_one(query, newvalues)  
            print("setting isomorphicTask of task "+row["taskid"]+" to "+isoName)
        else:
            query = { "taskid": row["taskid"] }
            newvalues = { "$set": { "isomorphicTask": None } }
            if do_implement:
                db.ctasks.update_one(query, newvalues)  
            print("skipping task "+row["taskid"])

if __name__ == "__main__":
    main()
