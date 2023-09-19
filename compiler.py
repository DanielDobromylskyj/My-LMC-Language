# Todo: Add Floating Point Numbers (floats), Using to memory chunks?
# Todo: Add Optomisation Pass if requested and remove any un-needed stuff e.g. : "STA xyz", "LDA xyz" as we dont need the "LDA xyz" chunk
# Todo: If Statements (Not Functioning)

# Errors
class ExportError(Exception): ...
class BuildError(Exception): ...
class ProgramError(Exception): ...

# Program
class Program:
    def __init__(self, code):
        self.code = code

        self.Compiled = []
        self.AfterHltCode = []
        self.LineNumber = 0

        self.Variables = []
        self.ValidTypes = ["int", "char"]
        self.VariableTypes = {}

        self.MultiplyUses = 0
        self.DivisionUses = 0
        self.LoopsUsed = 0
        self.IfsUsed = 0

    def Export(self, Type):
        if Type == "print":
            print("\n".join(self.Compiled) + "\nHLT\n" + "\n".join(self.AfterHltCode))
        else:
            raise ExportError(f"'{Type}' Is not a valid export type.")

    def build(self, IgnoreSizeLimit=False):
        # Declare Some Variables For The Program To Use
        self.DeclareVariable("int", "lmc_tmp1", 0)
        self.DeclareVariable("int", "lmc_tmp2", 0)
        self.DeclareVariable("int", "lmc_tmp3", 0)

        self.DeclareVariable("int", "lmc_charShift", 32)

        self.DeclareVariable("int", "CONST_VALUE_0", 0)
        self.DeclareVariable("int", "CONST_VALUE_1", 1)

        # Parse code / Build Program
        for rawLine in self.code.split("\n"):
            line: str = rawLine.lstrip(" ").rstrip(" ")

            if line.startswith("#") or line == "":
                self.LineNumber += 1
                continue

            if line.startswith("int") or line.startswith("char"):
                Type, Ident, _, Data = line.split(" ")
                self.DeclareVariable(Type, Ident, Data)

            elif line.startswith("OUTPUT"):
                _, Data = line.split(" ")
                self.Output(Data)

            elif line.startswith("LOOP"):
                if len(line.split(" ")) != 2:
                    raise BuildError(f"[Line {self.LineNumber}] Syntax Error")
                _, Ident1 = line.split(" ")
                self.StartLoop(Ident1)

            elif line.startswith("NEXT"):
                self.IterateLoop()

            elif line.startswith("IF"):
                _, Ident1, Sign, Ident2 = line.split(" ")
                self.DeclareIfStatement(Ident1, Sign, Ident2)

            elif line.startswith("ENDIF"):
                self.EndIfStatement()


            else:
                for variable in self.Variables:
                    if line.startswith(variable):
                        lineChunks = line.split(" ")

                        if len(lineChunks) == 5:
                            OutputIdent, _, Ident1, Sign, Ident2 = lineChunks
                            self.PerformMathOperation(OutputIdent, Ident1, Sign, Ident2)

                        elif len(lineChunks) == 3: # Move Data from a to b
                            Ident1, _, Ident2 = lineChunks
                            self.ShuffleVariables(Ident1, Ident2)

            self.LineNumber += 1




            # Perform Final Checks
        if (len(self.Compiled) > 99) and (IgnoreSizeLimit == False):
            raise ProgramError("Compiled Code is Too Large!")
        return self

    def ShuffleVariables(self, Ident1, Ident2):
        self.Compiled.extend([
            f"LDA {Ident2}",
            f"STA {Ident1}"
        ])
    def DeclareVariable(self, Type, Name, Data):
        if Name in self.Variables:
            raise BuildError(f"[Line {self.LineNumber}] '{Name}' is already in use. Can't be redefined")
        if Type not in self.ValidTypes:
            raise TypeError(f"[Line {self.LineNumber}] Invalid type: '{Type}'. Type doesn't exist")


        if Type == "int":
            if Data == 'INPUT':
                self.Compiled.extend([
                    f"INP",
                    f"STA {Name}",
                ])

                Data = 0

            elif Data in self.Variables:
                self.Compiled.extend([
                    f"LDA {Data}",
                    f"STA {Name}",
                ])

                Data = 0


            self.AfterHltCode.append(
                f"{Name} DAT {Data}"
            )

            self.Variables.append(Name)
            self.VariableTypes[Name] = Type

        elif Type == "char":
            if Data == "INPUT":
                raise BuildError("[Line {self.LineNumber}] 'char' Does not support 'INPUT' in this version")

            Data = ord(Data)

            self.AfterHltCode.append(
                f"{Name} DAT {Data}"
            )

            self.Variables.append(Name)
            self.VariableTypes[Name] = Type
    def Output(self, Data):
        if (Data.startswith('"')) or (Data.startswith("'")):
            raise BuildError("[Line {self.LineNumber}] Cant output characters or strings at the moment")

        elif Data in self.Variables:
            self.Compiled.extend([
                f"LDA {Data}",
                f"OUT",
            ])

        else:
            if f"CONST_VALUE_{Data}" not in self.Variables:
                self.DeclareVariable("int", f"CONST_VALUE_{Data}", Data)

            self.Compiled.extend([
                f"LDA CONST_VALUE_{Data}",
                f"OUT",
            ])
    def PerformMathOperation(self, OutputIdent, Ident1, Sign, Ident2):
        if Sign == "+":
            self.Compiled.extend([
                f"LDA {Ident1}",
                f"ADD {Ident2}",
                f"STA {OutputIdent}"
            ])

        elif Sign == "-":
            self.Compiled.extend([
                f"LDA {Ident1}",
                f"SUB {Ident2}",
                f"STA {OutputIdent}"
            ])
        elif Sign == "*":
            self.Compiled.extend([ # Multiplication Program
                f"LDA {Ident1}",
                f"STA lmc_tmp1",
                f"LDA CONST_VALUE_0",
                f"STA lmc_tmp2",
                f"MULLOOP{self.MultiplyUses} LDA lmc_tmp2",
                f"ADD {Ident2}",
                f"STA lmc_tmp2",
                f"LDA lmc_tmp1",
                f"SUB CONST_VALUE_1",
                f"STA lmc_tmp1",
                f"BRZ MULLOOP{self.MultiplyUses}_",
                f"BRP MULLOOP{self.MultiplyUses}",
                f"MULLOOP{self.MultiplyUses}_ LDA lmc_tmp2",
                f"STA {OutputIdent}",
            ])

            self.MultiplyUses += 1
        elif Sign == "/":
            self.Compiled.extend([
                f"LDA {Ident1}",
                f"STA lmc_tmp1",
                f"LDA CONST_VALUE_0",
                f"STA lmc_tmp2",
                f"BRA DIVSTART{self.DivisionUses}",
                f"DIVLOOP{self.DivisionUses} LDA lmc_tmp1",
                f"SUB {Ident2}",
                f"STA lmc_tmp1",
                f"LDA lmc_tmp2",
                f"ADD CONST_VALUE_1",
                f"STA lmc_tmp2",
                f"DIVSTART{self.DivisionUses} LDA lmc_tmp1",
                f"BRZ DIV_{self.DivisionUses}",
                f"BRP DIVLOOP{self.DivisionUses}",
                f"DIV_{self.DivisionUses} LDA lmc_tmp2",
                f"STA {OutputIdent}",
            ])

            self.DivisionUses += 1
        elif Sign == "%":
            self.Compiled.extend([
                f"LDA {Ident1}",
                f"STA lmc_tmp1",
                f"STA lmc_tmp3",
                f"LDA CONST_VALUE_0",
                f"STA lmc_tmp2",
                f"BRA DIVSTART{self.DivisionUses}",
                f"DIVLOOP{self.DivisionUses} LDA lmc_tmp1",
                f"STA lmc_tmp3",
                f"SUB {Ident2}",
                f"STA lmc_tmp1",
                f"LDA lmc_tmp2",
                f"ADD CONST_VALUE_1",
                f"STA lmc_tmp2",
                f"DIVSTART{self.DivisionUses} LDA lmc_tmp1",
                f"BRZ DIV_{self.DivisionUses}",
                f"BRP DIVLOOP{self.DivisionUses}",
                f"DIV_{self.DivisionUses} LDA lmc_tmp3",
                f"STA {OutputIdent}",
            ])

            self.DivisionUses += 1
        else:
            raise BuildError("[Line {self.LineNumber}] Invalid Operator (Sign) '{Sign}'")
    def StartLoop(self, Ident):
        self.DeclareVariable("int", f"lmc_LOOPCOUNTER{self.LoopsUsed}", 0)

        if Ident in self.Variables:
            if self.VariableTypes[Ident] != "int":
                raise BuildError("[Line {self.LineNumber}] Loop counter must be a int OR intVariable")

            self.Compiled.extend([
                f"LDA {Ident}",
                f"SUB CONST_VALUE_1",
                f"STA lmc_LOOPCOUNTER{self.LoopsUsed}"
            ])
        else:
            if f"CONST_VALUE_{Ident}" not in self.Variables:
                self.DeclareVariable("int", f"CONST_VALUE_{Ident}", Ident)

            self.Compiled.extend([
                f"LDA CONST_VALUE_{Ident}",
                f"SUB CONST_VALUE_1",
                f"STA lmc_LOOPCOUNTER{self.LoopsUsed}",
            ])

        self.Compiled.append(f"LOOP_POINTER{self.LoopsUsed} LDA lmc_tmp1") # Line does nothing but be a pointer (Cant be blank?)

        self.LoopsUsed += 1
    def IterateLoop(self):
        LoopID = self.LoopsUsed - 1

        self.Compiled.extend([
            f"LDA lmc_LOOPCOUNTER{LoopID}",
            f"BRZ lmc_LOOPCOUNTER{LoopID}_END",
            f"SUB CONST_VALUE_1",
            f"STA lmc_LOOPCOUNTER{LoopID}",
            f"BRA LOOP_POINTER{LoopID}",
            f"lmc_LOOPCOUNTER{LoopID}_END LDA lmc_tmp1", # Line does nothing but be a pointer
        ])

    def DeclareIfStatement(self, Ident1, Sign, Ident2):
        if Ident1 not in self.Variables:
            if f"CONST_VALUE_{Ident1}" not in self.Variables:
                self.DeclareVariable("int", f"CONST_VALUE_{Ident1}", Ident1)

            self.Compiled.extend([
                f"LDA CONST_VALUE_{Ident1}",
                f"STA lmc_tmp1",
            ])
        else:
            self.Compiled.extend([
                f"LDA {Ident1}",
                f"STA lmc_tmp1",
            ])

        if Ident2 not in self.Variables:
            if f"CONST_VALUE_{Ident2}" not in self.Variables:
                self.DeclareVariable("int", f"CONST_VALUE_{Ident2}", Ident2)

            self.Compiled.extend([
                f"LDA CONST_VALUE_{Ident2}",
                f"STA lmc_tmp2",
            ])
        else:
            self.Compiled.extend([
                f"LDA {Ident2}",
                f"STA lmc_tmp2",
            ])

        if Sign == "==":
            self.Compiled.extend([
                f"LDA lmc_tmp1",
                f"SUB lmc_tmp2",
                f"BRZ IF_SUCCEED{self.IfsUsed}",
                f"BRA IF_FAILED{self.IfsUsed}",
                f"IF_SUCCEED{self.IfsUsed} LDA lmc_tmp1",
            ])

        elif Sign == ">=":
            self.Compiled.extend([
                f"LDA lmc_tmp1",
                f"SUB lmc_tmp2",
                f"BRP IF_SUCCEED{self.IfsUsed}",
                f"BRA IF_FAILED{self.IfsUsed}",
                f"IF_SUCCEED{self.IfsUsed} LDA lmc_tmp1",
            ])
        elif Sign == "<=":
            self.Compiled.extend([
                f"LDA lmc_tmp2",
                f"SUB lmc_tmp1",
                f"BRP IF_SUCCEED{self.IfsUsed}",
                f"BRA IF_FAILED{self.IfsUsed}",
                f"IF_SUCCEED{self.IfsUsed} LDA lmc_tmp1",
            ])
        elif Sign == ">":
            self.Compiled.extend([
                f"LDA lmc_tmp1",
                f"SUB lmc_tmp2",
                f"BRZ IF_FAILED{self.IfsUsed}",
                f"BRP IF_SUCCEED{self.IfsUsed}",
                f"BRA IF_FAILED{self.IfsUsed}",
                f"IF_SUCCEED{self.IfsUsed} LDA lmc_tmp1",
            ])
        elif Sign == "<":
            self.Compiled.extend([
                f"LDA lmc_tmp2",
                f"SUB lmc_tmp1",
                f"BRZ IF_FAILED{self.IfsUsed}",
                f"BRP IF_SUCCEED{self.IfsUsed}",
                f"BRA IF_FAILED{self.IfsUsed}",
                f"IF_SUCCEED{self.IfsUsed} LDA lmc_tmp1",
            ])
        else:
            raise BuildError(f"[Line {self.LineNumber}] Unknown Sign '{Sign}'")

        self.IfsUsed += 1

    def EndIfStatement(self):
        self.Compiled.append(f"IF_FAILED{self.IfsUsed - 1} LDA lmc_tmp1")



if __name__ == "__main__":
    code = """
    # >> Fib Sequence!
    # Calculates the first X (Input) numbers of the Fib sequence
    int count = INPUT
    int num1 = 1
    int num2 = 0
    int num3 = 0
    
    LOOP count
        OUTPUT num1
        
        num3 = num1 + num2
        num2 = num1
        num1 = num3
    
    NEXT
    
    """

    MyProgram = Program(code).build()
    MyProgram.Export("print")