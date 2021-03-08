# -*- coding: future_fstrings -*-
# Import packages
from json import JSONEncoder

class CustomEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, SingleCondition):
            return object.__dict__
        elif isinstance(object, Lexer):
            return object.__dict__
        else:
            # call base class implementation which takes care of
            return json.JSONEncoder.default(self, object)


class Status:
    def __init__(self):
        self.error = None
        self.offset = 0
        self.error_offset = 0


class SingleCondition:
    def __init__(self, condition_string, status):
        ''' Inputs: condition_string, type string
                    status, type Status instance'''
        self.variables = []  # type [str]
        self.values_integers = []  # type [int]
        self.values_string = [] # type [str] 
        if '==' in condition_string:
            self.op = "EQUAL"
            frags = condition_string.split('==')
            self.condition_fragments(frags, condition_string, status)
            return
        if '!=' in condition_string:
            self.op = "NOTEQUAL"
            frags = condition_string.split("!=")
            self.condition_fragments(frags, condition_string, status)
            return
        if '>=' in condition_string:
            self.op = "GREATEREQUAL"
            frags = condition_string.split(">=")
            self.condition_fragments(frags, condition_string, status)
            return
        if '<=' in condition_string:
            self.op = "LESSEQUAL"
            frags = condition_string.split("<=")
            self.condition_fragments(frags, condition_string, status)
            return
        if 'notinset{' in condition_string:
            if condition_string.startswith("notinset{") and condition_string[-1]=="}":
                self.op = "NOTINSET"
                fields=condition_string[len("notinset{"):-1].split(",")
                if len(fields)==2:
                    self.variables.append(fields[0].strip())
                    self.variables.append(fields[1].strip())
                else:
                    status.error=f"{condition_string} needs to have two arguments"
                return
            else:
                status.error=f"{condition_string} is not a valid notinset condition"
                return
            return
        if 'inset{' in condition_string:
            if condition_string.startswith("inset{") and condition_string[-1]=="}":
                self.op = "INSET"
                fields=condition_string[len("inset{"):-1].split(",")
                if len(fields)==2:
                    self.variables.append(fields[0].strip())
                    self.variables.append(fields[1].strip())
                else:
                    status.error=f"{condition_string} needs to have two arguments"
                return
            else:
                status.error=f"{condition_string} is not a valid inset condition"
                return
            return
        if 'exists{' in condition_string:
            if condition_string.startswith("exists{") and condition_string[-1]=="}":
                self.op = "EXISTS"
                field=condition_string[len("exists{"):-1]
                self.variables.append(field);
                return
            else:
                status.error=f"{condition_string} is not a valid exists condition"
                return
            return
        status.error = f"{condition_string} is an invalid condition"

    def condition_fragments(self, frags, condition_string, status):
        ''' Inputs: frags, type string list
                    condition_string, type string
                    status, type Status instance'''
        if len(frags) != 2:
            status.error = f"{condition_string} is an invalid condition"
            return
        self.variables=frags[0].strip().split("+")
        # check if second argument is a number, string or other variable
        argument = frags[1].strip()
        if argument[0] == '"':
            if (argument[-1] != '"') or (len(argument) < 2):
                status.error = f"{argument} in {condition_string} is an invalid string"
                return
            argument = argument[1: len(argument)-1].strip()
            if argument == "":
                status.error = f"{argument} in {condition_string} is an invalid string"
                return
            if len(self.variables)>1:
                status.error = f"{argument} in {condition_string} is a string but the left-hand side adds integer variables"
                return
            self.values_string.append(argument)
            return
        if argument[-1] == '"':
            # starts without quotation mark but ends with quotation
            status.error = f"{argument} in {condition_string} is an invalid string"
            return
        # check if integer
        try:
            value=int(argument)
            self.values_integers.append(value)			
        except:
            if len(self.variables)>1:
                status.error = f"{argument} in {condition_string} is a string but the left-hand side adds integer variables"
                return
            self.values_string.append(argument)

    def serialize_single_cond(self):
        if self.op!="NOTINSET" and self.op!="INSET":
            sb = "+".join(self.variables)
        else:
            sb=""
        if self.op == "EQUAL":
            sb += "=="
        elif self.op == "NOTEQUAL":
            sb += "!="
        elif self.op == "GREATEREQUAL":
            sb += ">="
        elif self.op == "LESSEQUAL":
            sb += "<="
        elif self.op == "NOTINSET":
            sb += "notinset{"
            sb +=self.variables[0]
            sb +=","
            sb +=self.variables[1]
            sb +="}"
        elif self.op == "INSET":
            sb += "inset{"
            sb +=self.variables[0]
            sb +=","
            sb +=self.variables[1]
            sb +="}"
        elif self.op == "EXISTS":
            sb += "exists{"
            sb +=self.variables[0]
            sb +="}"
        if len(self.values_integers) > 0:
            sb += str(self.values_integers[0])
        elif len(self.values_string)>0:
            sb += "\""
            sb += self.values_string[0]
            sb += "\""
        return sb

    def check_condition_single_cond(self, all_variables,all_sets, status):
        ''' Inputs: all_variables, type {str: str}
                    status, type Status instance
            Output: bool '''
        if self.op == "NOTINSET":
            return self.check_notinset_cond(all_variables,all_sets,status)
        if self.op == "INSET":
            return self.check_inset_cond(all_variables,all_sets,status)
        if self.op == "EXISTS":
            return self.check_exists_cond(all_variables,status)
        status.error = None
        LHS_sum=0
        LHS=""
        for var in self.variables:
           if not(var in all_variables):
              #status.error = f"cannot check condition {self.serialize_single_cond()}: variable {var} is undefined"
              #we don't return False if it's an adding-up condition
              if not len(self.variables) > 1:
                return False
        if len(self.values_integers) > 0:
           # we have an integer
           for var in self.variables:
               try:
                  if var in all_variables:
                    LHS_sum+=int(all_variables[var])
               except:
                  status.error = f"cannot check condition {self.serialize_single_cond()}: variable value {all_variables[var]} is not an integer"
                  return False
        else:
            LHS=all_variables[self.variables[0]]
        if self.op == "EQUAL":
            if len(self.values_integers) > 0:
                return LHS_sum==self.values_integers[0]
            else:
                # we have a string value
                return LHS==self.values_string[0]
        elif self.op == "NOTEQUAL":
            if len(self.values_integers) > 0:
                return LHS_sum!=self.values_integers[0]
            else:
                # we have a string value
                return LHS!=self.values_string[0]
        elif self.op == "GREATEREQUAL":
            return LHS_sum>=self.values_integers[0]
        elif self.op == "LESSEQUAL":
            return LHS_sum<=self.values_integers[0]
        return False

    def check_notinset_cond(self, all_variables,all_sets, status):
        ''' Inputs: all_variables, type {str: str}
                    status, type Status instance
            Output: bool '''
        #convert everything to string
        if self.variables[0] not in all_variables:
            status.error = f"cannot check condition {self.serialize_single_cond()}: variable {self.variables[0]} is undefined"
            return False
        if self.variables[1] not in all_sets:
            status.error = f"cannot check condition {self.serialize_single_cond()}: set {self.variables[1]} is undefined"
            return False
        LHS=str(all_variables[self.variables[0]])
        print(all_sets)
        print(LHS)
        print(self.variables[1])
        print(LHS not in all_sets[self.variables[1]])
        raise Exception("stop here")
        return LHS not in all_sets[self.variables[1]]

    def check_inset_cond(self, all_variables,all_sets, status):
        ''' Inputs: all_variables, type {str: str}
                    status, type Status instance
            Output: bool '''
        #convert everything to string
        if self.variables[0] not in all_variables:
            status.error = f"cannot check condition {self.serialize_single_cond()}: variable {self.variables[0]} is undefined"
            return False
        if self.variables[1] not in all_sets:
            status.error = f"cannot check condition {self.serialize_single_cond()}: set {self.variables[1]} is undefined"
            return False
        LHS=str(all_variables[self.variables[0]])
        return LHS in all_sets[self.variables[1]]

    def check_exists_cond(self, all_variables, status):
        ''' Inputs: all_variables, type {str: str}
                    status, type Status instance
            Output: bool '''
        if self.variables[0].endswith("*"):
            prefix=self.variables[0][0:-1]
            return (prefix in all_variables)
        else:
            return (self.variables[0] in all_variables)

class Lexer:
    def __init__(self):
        ''' Inputs: conditions, type SingleCondition list
                    fragments, type Lexer list
                    logical, type LogicalOperator '''
        self.conditions = []
        self.fragments = []
        self.logical = "NONE"
        self.varlist=[]
        self.setlist=[]

    def __str__(self):
        return "conditions: " + str(self.conditions) + " fragments: " + str([str(f) for f in self.fragments]) + " logical: " + str(self.logical)

    def can_import(self, condition_str, status):
        if self.can_import_worker(0,condition_str,status):
            self.get_variables(status)
            if status.error!=None:
                return False
            return True
        else:
            return False

    def can_import_worker(self, depth, condition_str, status):
        ''' Inputs: depth, type int
                    condition_str, type string
                    status, type Status instance
                    offset, type int, *reference*
                    error, type string, *out*
                    error_offset, type int, *out*
             Output: bool'''
        text = ""
        while True:
            # check if we reached the end
            if status.offset == len(condition_str):
                if not(self.check_condition(text, status)):
                    return False
                # next check if there are any conditions
                if len(self.conditions) + len(self.fragments) == 0:
                    status.error_offset = status.offset
                    error = f"condition ending in position {status.offset} is empty"
                    return False
                if depth > 0:
                    status.error_offset = status.offset
                    status.error = f"condition ending in position {status.offset} has opening bracket but no closing bracket"
                    return False
                return True
            if condition_str[status.offset] == '(':
                status.offset += 1
                frag = Lexer()
                self.fragments.append(frag)
                if not(frag.can_import_worker(depth+1, condition_str, status)):
                    return False
                continue
            if condition_str[status.offset] == ')':
                if depth == 0:
                    status.error_offset = status.offset
                    status.error = f"bracket closes at position {status.offset} but no corresponding open bracket"
                    return False
                if not(self.check_condition(text, status)):
                    return False
                # next check if there are any conditions
                if len(self.conditions) + len(self.fragments) == 0:
                    status.error_offset = status.offset
                    status.error = f"condition ending in position {status.offset} is empty"
                    return False
                status.offset += 1
                return True
            if (condition_str[status.offset] == '&') or (condition_str[status.offset] == '|'):
                op = "AND"
                otherop = "OR"
                if condition_str[status.offset] == '|':
                    op = "OR"
                    otherop = "AND"
                if not(self.check_condition(text, status)):
                    return False
                text = ""
                # next check if there are any conditions
                if len(self.conditions) + len(self.fragments) == 0:
                    status.error_offset = status.offset
                    error = f"{op} symbol at position {status.offset} is not preceded by any conditions"
                    return False
                if self.logical == otherop:
                    status.error_offset = status.offset
                    status.error = f"{op} symbol at position {status.offset} is preceded by {otherop} condition"
                    return False
                self.logical = op
                status.offset += 1
                continue
            text += condition_str[status.offset]
            status.offset += 1


    def check_condition(self, text, status):
        ''' Inputs: text, type string,
                    offset, type int
                    error, type string, *out*
                    error_offset, type int, *out*
            Output: bool'''
        status.error = None
        status.error_offset = -1
        # check if we can add a condition
        text = text.strip()
        if text != "":
            cond = SingleCondition(text, status)
            if status.error is not None:
                return False
            self.conditions.append(cond)
        return True

    def serialize(self):
        ''' Output: string or None type '''
        frags = []
        for c in self.conditions:
            frags.append(c.serialize_single_cond())
        for f in self.fragments:
            frags.append("(" + str(f.serialize()) + ")")
        if self.logical == "NONE":
            return frags[0]
        elif self.logical == "AND":
            return "&".join(frags)
        elif self.logical == "OR":
            return "|".join(frags)
        else:
            return ""

    def get_variables(self,status):
        self.varlist=[]
        self.setlist=[]
        for cond in self.conditions:
            if cond.op=="NOTINSET" or cond.op=="INSET":
                self.varlist.append(cond.variables[0])
                self.setlist.append(cond.variables[1])
            else:
                for v in cond.variables:
                    if v not in self.varlist:
                        self.varlist.append(v)
        for frag in self.fragments:
            frag.get_variables(status)
            for v in frag.varlist:
                if v not in self.varlist:
                    self.varlist.append(v)
            for s in frag.setlist:
                if s not in self.setlist:
                    self.setlist.append(s)


    def check_conditions(self, variables, sets, status):
        '''Inputs: variables, type {str: str}
                    status, type Status instance
            Output: bool'''
        status.error = None
        condition_values = []
        for c in self.conditions:
            condition_values.append(c.check_condition_single_cond(variables,sets, status))
            if status.error is not None:
                return False

        for f in self.fragments:
            condition_values.append(f.check_conditions(variables,sets, status))
            if status.error is not None:
                return False

        if self.logical == "NONE":
            return condition_values[0]
        elif self.logical == "AND":
            sum = True
            for c in condition_values:
                sum = sum and c
            return sum
        elif self.logical == "OR":
            sum = False
            for c in condition_values:
                sum = sum or c
            return sum
        return True


