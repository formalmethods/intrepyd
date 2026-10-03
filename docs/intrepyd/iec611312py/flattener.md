Module intrepyd.iec611312py.flattener
=====================================
This module implements a flattener for ST terms

Functions
---------

    
`build_ite(var_occ, conditions, rewritten_stmt_blocks)`
:   

    
`collect_lhss(blocks)`
:   

    
`find_rhs_for(var_occ, block)`
:   

Classes
-------

`Flattener()`
:   Flattens statements

    ### Methods

    `flatten_case(self, instruction)`
    :

    `flatten_if_then_else(self, instruction)`
    :

    `flatten_instruction(self, instruction)`
    :

    `flatten_stmt_block(self, block)`
    :   Flatten a statement block