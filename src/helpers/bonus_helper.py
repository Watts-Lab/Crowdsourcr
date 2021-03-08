from helpers import jaccard_machine

class BonusType(object) :
    def __init__(self) :
        pass
    @classmethod
    def calculate_bonus(cls, bonus_info, agreed, total):
        if bonus_info['type']=="linear":
            return LinearBonusType.calculate_bonus(bonus_info=bonus_info,agreed=agreed,total=total)
        if bonus_info['type']=="threshold":
            return ThresholdBonusType.calculate_bonus(bonus_info=bonus_info,agreed=agreed,total=total)
        raise Exception('Error: unsupported bonus type %s' % (bonus_info['type']))

class LinearBonusType(BonusType) :
    bonusType = 'linear'
    @staticmethod
    def calculate_bonus(bonus_info, agreed, total) :
        consenters = max(0.0, agreed - 1.0)
        amt = bonus_info['bonuspoints'] * (consenters / total) * (total / max((total - 1.0), 1.0))
        exp = '%s bonus points for agreeing with %d of the %d other workers on a question with linear payment and maximal bonus points of %s' % (amt, consenters, total - 1, bonus_info['bonuspoints'])
        return (amt, exp)

class ThresholdBonusType(BonusType) :
    bonusType = 'threshold'
    @staticmethod
    def calculate_bonus(bonus_info, agreed, total) :
        amt = bonus_info['bonuspoints'] if 100.0 * agreed / total >= bonus_info['threshold'] else 0.0
        exp = '%s bonus points for agreeing with %d of %d workers on a question with threshold payment set at %d and maximal bonus points of %s' % (amt, agreed, total, bonus_info['threshold'], bonus_info['bonuspoints'])
        return (amt, exp)


def calculate_worker_bonus_info(possible_bonus_points, bonusDetails, moduleVarnameValuetype) :
    raw_bonus = calculate_raw_bonus_info(possible_bonus_points, bonusDetails, moduleVarnameValuetype)
    return normalize_bonus_info(raw_bonus)

def calculate_raw_bonus_info(possible_bonus_points, bonusDetails, moduleVarnameValuetype) :
    #calculate unnormalized bonus
    worker_bonus_info = {}
    for task,taskDetails in bonusDetails.items():
        for module,moduleDetails in taskDetails.items():
            for varname,questionDetails in moduleDetails.items():
                total_responses=1.0 * len(questionDetails["possibleWorkers"])
                #cycle over the workers
                for workerid,response in questionDetails["actualWorkers"].items():
                    if workerid not in worker_bonus_info:
                        worker_bonus_info.setdefault(workerid, {'earned' : 0.0, 'possible' : 1.0*possible_bonus_points,'exp' : []})
                    #now compare with all the other workers
                    agreed=1
                    for otherworkerid,otherresponse in questionDetails["actualWorkers"].items():
                        if workerid==otherworkerid:
                            continue
                        if moduleVarnameValuetype[module][varname]["valuetype"]=="imageupload":
                            if response-otherresponse<20:
                                agreed=agreed+1
                        elif moduleVarnameValuetype[module][varname]["valuetype"]=="approximatetext":
                            jaccard=jaccard_machine.getJaccard()
                            if jaccard.compare(response,otherresponse)>0.75:
                                agreed=agreed+1
                        else:
                            if response==otherresponse:
                                agreed=agreed+1
                    agreed=1.0*agreed
                    bonus_info=questionDetails['bonus']
                    bonus_amount, bonus_exp = BonusType.calculate_bonus(bonus_info=bonus_info,
                                                                        agreed=agreed,
                                                                        total=total_responses)
                    if moduleVarnameValuetype[module][varname]["valuetype"]=="imageupload":
                        bonus_exp = 'On image task %s, question %s_%s, for response %s: %s' % (task, module, varname, response, bonus_exp)
                    elif moduleVarnameValuetype[module][varname]["valuetype"]=="approximatetext":
                        bonus_exp = 'On approximate text task %s, question %s_%s, for response %s: %s' % (task, module, varname, response, bonus_exp)
                    else:
                        bonus_exp = 'On task %s, question %s_%s, for response %s: %s' % (task, module, varname, response, bonus_exp)
                    worker_bonus_info[workerid]['earned'] += bonus_amount
                    worker_bonus_info[workerid]['exp'].append(bonus_exp)
                #add explainer for workers who did not answer this question
                for workerid in questionDetails["possibleWorkers"]:
                    if workerid not in worker_bonus_info:
                        worker_bonus_info.setdefault(workerid, {'earned' : 0.0, 'possible' : 1.0*possible_bonus_points,'exp' : []})
                    if workerid not in questionDetails["actualWorkers"]:
                        bonus_exp = 'On task %s, question %s_%s was not shown.' % (task, module, varname)
                        worker_bonus_info[workerid]['exp'].append(bonus_exp)
    print(worker_bonus_info)
    return worker_bonus_info

def normalize_bonus_info(worker_bonus_info) :
    worker_bonus_percent = { a :
                            {'pct' : 0 if worker_bonus_info[a]['possible'] == 0 else (worker_bonus_info[a]['earned'] / worker_bonus_info[a]['possible']),
                             'earn' : worker_bonus_info[a]['earned'],
                             'poss' : worker_bonus_info[a]['possible'],
                             'exp' : worker_bonus_info[a]['exp']}
                             for a in worker_bonus_info}
    min_bonus_percent = 0.0
    max_bonus_percent = 1.0
    if len(worker_bonus_percent) > 0 :
        worst_worker = min(worker_bonus_percent.keys(),
                          key=(lambda key: worker_bonus_percent[key]['pct']))
        best_worker = max(worker_bonus_percent.keys(),
                          key=(lambda key: worker_bonus_percent[key]['pct']))
        if (worker_bonus_percent[worst_worker]['pct'] != worker_bonus_percent[best_worker]['pct']) and worker_bonus_percent[best_worker]['pct'] > 0.0:
            min_bonus_percent = worker_bonus_percent[worst_worker]['pct']
            max_bonus_percent = worker_bonus_percent[best_worker]['pct']
    # scale by maximum -- minimum
    worker_bonus_percent = {a.upper().strip() :
                            { 'pct' : (worker_bonus_percent[a]['pct'] - min_bonus_percent) / (max_bonus_percent - min_bonus_percent),
                              'earn' : worker_bonus_percent[a]['earn'],
                              'poss' : worker_bonus_percent[a]['poss'],
                              'exp' : worker_bonus_percent[a]['exp'],
                              'rawpct' : worker_bonus_percent[a]['pct'],
                              'worst' : min_bonus_percent,
                              'best' : max_bonus_percent}
                            for a in worker_bonus_percent}

    print(worker_bonus_percent)

    return worker_bonus_percent
