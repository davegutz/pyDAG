#!/usr/bin/env python

from simpleparse.parser import Parser

def printResultTree( tree, indent="" ) :
    for i in tree :
        print indent, i[0], i[1], i[2]
        #printResultTree(i[3],"  %s" % indent)
        if i[3] and len(i[3]) : printResultTree(i[3],"  %s" % indent)

# First define the parsing EBNF grammer
grammer = r"""
    <semicolon>   := ';'
    <colon>       := ':'
    <equal>       := '='
    <ampersand>   := '&'
    lbracket      := '['
    rbracket      := ']'
    lparen        := '('
    rparen        := ')'
    <minus>       := '-'
    <plus>        := "+"
    <sign>        := plus / minus
    
    <alphas>      := [a-zA-Z]
    <digits>      := [0-9]
    <alphanums>   := (alphas / digits)
    
    <ws>          := [ \t\r\n]
    
    word          := alphas, ('_' / alphanums)*
    blockWord     := ('_' / alphanums)*
    numbers       := sign?, digits+
    float         := sign?, digits*, ".", digits*

    quoteString   := '"', ('""'/-["])*, '"'
    quotedList    := quoteString, (',', ws*, quoteString)*

    range         := lbracket, word, ws, colon, ws, word, rbracket

    month         := "Jan" / "Feb" / "Mar" / "Apr" / "May" / "Jun" / "Jul"
                        / "Aug" / "Sep" / "Oct" / "Nov" / "Dec"
    day           := digits, digits
    year          := digits, digits, digits, digits
    date          := day, "-", month, "-", year
    hour          := digits, digits
    min           := digits, digits
    sec           := digits, digits
    time          := hour, ":", min, ":", sec

    false         := "FALSE"
    true          := "TRUE"
    boolValue     := false / true

    null          := "NULL"
    nullFlag      := null, semicolon
    localFlag     := "LOCAL", semicolon

    netlistBegin  := "NETLIST_BEGIN IS"
    systemVersion := "SYSTEM VERSION", ws, word, semicolon
    codegenVersion := "REQUIRED CODEGEN VERSION", ws, word, semicolon
    fileName      := "FILE_NAME", ws, quoteString, semicolon
    targetLanguage:= "TARGET_LANGUAGE", ws, equal, ws, word, semicolon
    topNet        := "TOP_NET", ws, equal, ws, word, semicolon
    precision     := "PRECISION", ws, equal, ws, word, semicolon
    arithmetic    := "ARITHMETIC", ws, equal, ws, word, semicolon
    tableDataDecl := "TABLE_DATADECL", ws, equal, ws, word, semicolon
    variableDecl  := "VARIABLE_DECL", ws, equal, ws, word, semicolon
    adaCodegen    := "ADA_CODEGEN", ws, equal, ws, word, semicolon
    defICFlag     := "DEF_ICFLAG", ws, equal, ws, word, semicolon
    caseRule      := "CASE_RULE", ws, equal, ws, word, semicolon
    librariesExp  := "LIBRARIES_EXPORTED_BEGIN", ws+, quotedList, semicolon,
                        ws+, "LIBRARIES_EXPORTED_END", semicolon
    libraries     := "LIBRARIES_IMPORTED_BEGIN", ws+, quotedList, semicolon,
                        ws+, "LIBRARIES_IMPORTED_END", semicolon

    globalDataDecS:= "GLOBAL_DATA_DECLARATIONS_BEGIN"
    sectionBegin  := "SECTION_BEGIN", ws, word, ws, "IS"
    typedefBegin  := "TYPEDEF_BEGIN"
    datatypeBegin := "DATATYPE_BEGIN", ws, word, ws, "IS"
    datatypeEnd   := "DATATYPE_END", semicolon
    datatype      := datatypeBegin, -datatypeEnd*, datatypeEnd
    datatypes     := datatype, (ws+, datatype)*
    typedefEnd    := "TYPEDEF_END", semicolon
    typedefList   := typedefBegin, ws+, datatypes, ws+, typedefEnd
    
    var           := "VAR"
    state         := "STATE"
    con           := "CON"
    symbolType    := var / state / con
    
    manualBScale  := ampersand, "MANUAL_BSCALE", equal, numbers
    noBScale      := ampersand, "NO_SCALING"
    scaling       := manualBScale / noBScale
    
    intType       := "INTEGER"
    uintType      := "UNSIGNED_INTEGER"
    longType      := "LONG"
    ulongType     := "UNSIGNED_LONG"
    realType      := "REAL"
    blongType     := "BLong"
    bwordType     := "BWord"
    udtType       := word
    boolType      := "BOOLEAN", ws, noBScale, ws, range
    varType       := intType / uintType / longType / ulongType / realType /
                        blongType / bwordType / boolType / udtType
    
    varBegin      := "VAR_BEGIN"
    variable      := word, ws, colon, ws, symbolType, ws, varType,
                        (ws, scaling)?, ws, equal,
                        ws, (null / float / numbers / boolValue ),
                        semicolon
    varEnd        := "VAR_END", semicolon
    varList       := varBegin, (ws+, variable)+, ws+, varEnd
    
    sectionEnd    := "SECTION_END", semicolon
    section       := sectionBegin,
                        (ws+, localFlag)?,
                        ws+, nullFlag,
                        (ws+, typedefList)?,
                        (ws+, varList)?,
                        ws+, sectionEnd
    sections      := section, (ws+, section)*
    globalDataDecE:= "GLOBAL_DATA_DECLARATIONS_END", semicolon
    globaldatadec := globalDataDecS, ws+, sections, ws+, globalDataDecE

    netInfoStart  := "NET_BEGIN", ws+, word, ws+, "IS"
    created       := "CREATED", ws, date, ws, time, semicolon
    modified      := "MODIFIED", ws, date, ws, time, semicolon
    blocksUsed    := "BLOCKS_USED_BEGIN", ws+, quotedList, semicolon, ws+,
                        "BLOCKS_USED_END", semicolon
    header        := "HEADER_BEGIN", ws+, created, ws+, modified, ws+,
                        blocksUsed, ws+, "HEADER_END", semicolon

    procedure     := "PROCEDURE", ws+, word, semicolon
    mainFlag      := "MAIN_NET", semicolon
    discreteFlag  := "DISCRETE", semicolon
    sampleRate    := "SAMPLE_RATE", ws, equal, ws, float, semicolon
    sampleOffset  := "SAMPLE_OFFSET", ws, equal, ws, float, semicolon
    type          := "TYPE_BEGIN", ws+, procedure, (ws+, mainFlag)?,
                        (ws+, discreteFlag)?, ws+, sampleRate, ws+,
                        sampleOffset, ws+, "TYPE_END", semicolon

    revHeader     := "REVISION_HEADER_BEGIN", ws+, quoteString, ws+,
                        "REVISION_HEADER_END", semicolon
    
    description   := "description_nam", ws, colon, ws, "STRING", ws, equal,
                        ws, quoteString, semicolon
    field1        := "field1", ws, colon, ws, "STRING", ws, equal,
                        ws, quoteString, semicolon
    field2        := "field2", ws, colon, ws, "STRING", ws, equal,
                        ws, quoteString, semicolon
    field3        := "field3", ws, colon, ws, "STRING", ws, equal,
                        ws, quoteString, semicolon
    
    titleBlock    := "TITLE_BLOCK_BEGIN", ws+, description, ws+, field1,
                        ws+, field2, ws+, field3, ws+, "TITLE_BLOCK_END",
                        semicolon

    noScalingInfo := ampersand, "NO_SCALING", ws, lbracket, boolValue, ws,
                        colon, ws, boolValue, rbracket
    formalDecl    := word, lparen, numbers, rparen, ws, colon, ws, word,
                        ws, word, (ws, noScalingInfo)?, semicolon
    formalsList   := (formalDecl / nullFlag), (ws+, formalDecl)*
    formalParams  := "FORMAL_PARAMETERS_BEGIN", lparen, numbers, rparen,
                        ws+, formalsList, ws+, "FORMAL_PARAMETERS_END",
                        semicolon
                        
    comment       := "COMMENT_BEGIN", ws+, quoteString, semicolon, ws+,
                        "COMMENT_END", semicolon
    
    dataDecStart  := "DATA_DECLARATIONS_BEGIN"
    dataDecEnd    := "DATA_DECLARATIONS_END", semicolon
    datadec       := dataDecStart, -dataDecEnd*, dataDecEnd

    subnetNumber  := lparen, numbers, rparen
    blockType     := "BLOCK_TYPE", ws, quoteString, (ws, subnetNumber)?,
                        semicolon
    blockName     := "BLOCK_NAME", ws, word, semicolon
    blockNumber   := "BLOCK_NUMBER", ws, equal, ws, numbers, semicolon
    loopBreakFlagI:= "LOOPBREAKER_INPUT", semicolon
    loopBreakFlagO:= "LOOPBREAKER_OUTPUT", semicolon
    hierarchyInfo := "HIERARCHICAL", (ws, "STUBBED")?, ws,
                        ("EXTERNAL"/"LIBRARY"), ws,
                        "PROCEDURE SIGNAL_BLOCKS", ws, word, semicolon
    blockTypeInfo := "TYPE_BEGIN", ws+, (blockType/hierarchyInfo),
                        (ws+, blockName)?,
                        (ws+, loopBreakFlagI/loopBreakFlagO)?, ws+,
                        blockNumber, ws+, "TYPE_END", semicolon
    
    actParamInfo  := "ACTUAL_PARAMETERS_BEGIN", -"ACTUAL_PARAMETERS_END"*,
                        "ACTUAL_PARAMETERS_END", semicolon
    forParamInfo  := "PARAMETERS_BEGIN", -"PARAMETERS_END"*,
                        "PARAMETERS_END", semicolon
    
    outputInfo    := "OUTPUT_BEGIN", -"OUTPUT_END"*, "OUTPUT_END", semicolon
    stateInfo     := "STATE_BEGIN", -"STATE_END"*, "STATE_END", semicolon
    inputInfo     := "INPUT_BEGIN", -"INPUT_END"*, "INPUT_END", semicolon
    bodyInfo      := "BODY_BEGIN", -"BODY_END"*, "BODY_END", semicolon
    
    blockInfo     := "BLOCK_BEGIN", ws, blockWord, ws, "IS", ws+,
                        blockTypeInfo, (ws+, comment)?,
                        (ws+, actParamInfo)?, (ws+, forParamInfo)?,
                        (ws+, outputInfo/stateInfo/inputInfo/bodyInfo)*,
                        ws+, "BLOCK_END", ws, blockWord, semicolon
    blockList     := blockInfo, (ws+, blockInfo)*

    netInfoEnd    := "NET_END", ws, word, semicolon
    netInfo       := netInfoStart,
                        ws+, header, ws+,
                        type, ws+, revHeader, ws+, titleBlock,
                        (ws+, comment)?, ws+, formalParams,
                        (ws+, datadec)?, ws+, blockList, ws+,
                        #-"NET_END"*,
                        netInfoEnd

    
    netlistEnd    := "NETLIST_END", semicolon
    
    NetList       := netlistBegin, ws+, systemVersion, ws+, codegenVersion,
                        ws+, fileName, ws+, targetLanguage, ws+, topNet,
                        ws+, precision, ws+, arithmetic, ws+, tableDataDecl,
                        ws+, variableDecl, ws+, adaCodegen, (ws+, defICFlag)?,
                        (ws+, caseRule)?, (ws+, librariesExp)?,
                        (ws+, libraries)?, (ws+, globaldatadec)?,
                        (ws+, netInfo)+, ws+,
                        #-netlistEnd*,
                        netlistEnd
"""
class netlistParser( Parser ) :
    def __init__( self, decl, root ) :
        Parser.__init__( self, decl, root )
        self.netlistPrebuilt = None
        
    def buildTagger( self, production=None, processor=None ) :
        if self.netlistPrebuilt is None :
            self.netlistPrebuilt = Parser.buildTagger( self, production, processor )
        return self.netlistPrebuilt

import sys
if __name__=="__main__":
    parser = netlistParser( grammer, "NetList" )
    # Open file and read contents
    if len(sys.argv) > 1:
        fname=sys.argv[1]
    else:
        fname="rwf12.net"
    netfile = open( fname, "r" )
    #  Local version of contents below is for speed (prevents dereferencing
    #  the self.contents everytime
    contents = netfile.read()
    netlist_start = contents.find("NETLIST_BEGIN IS")
    netlist_end = contents.find("NETLIST_END;",netlist_start) + len("NETLIST_END;")
    contents = contents[netlist_start:netlist_end]
               
    results = parser.parse( contents )
    if not results[0] :
            print fname
            mh.message("Netlist Parse Error: %s" % __name__)
            mh.store("ParseError", fname)
               

    #print '\n\ncontents=', contents, '\n\n'
    #print 'results=\n', results, '\n\n'
    print 'resultTree=\n', printResultTree(results[1]), '\n\n'

    # Process the results
    for i in results[1] :
        tmp = "_%s" % i[0]
        print i,tmp
        #if hasattr(tmp) :
            #getattr(tmp)(i)


