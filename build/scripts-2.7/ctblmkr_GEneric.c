/* ************************************************************
file: ctblmkr.c

Converts: standard, FSIM/Software FORTRAN NAME LIST tables
          to BEACON ANSI-C with lookup=INLINE_DECLARATIONS.

Usage:    ctblmkr input-filename output-filename
   This will read the input-file, which should consist of
   FORTRAN NAMELIST type table definitions, and write two output
   files: (1) the file specified, which will contain C static
   constant initializers defining the tables.  This file
   should be compiled and linked with the other object files.
   (2) a file with the same root as (1) but with "2.h" appended
   (e.g. if ctbl.h is the output-filename, the second file
   will be called ctbl2.h).  The second file contains extern
   declarations of the tables, for inclusion in C source files.

History:        
   Version 1.0 - Jerry A. Swan - written.
   Version 1.1 - P. Shaffer 7/2/97 - added ability to
      handle x.xxE+yy numbers, and blanks at end of table names.
   Version 1.2 - P. Shaffer 8/21/98 - added check for exceeding
      number of points in X, Y, or Z arrays.  Remove output file on error.
      Return -1 on error, 0 elsewise (for compatibility with make).
      Make tolerant of spaces after values.
   Version 1.3 - P. Shaffer 10/2/98 - added 4-D Table capability.

   Version 1.4 - /j. Swan 09/17/01 - updated to write: 
     tables_def.h  ( rootname )   contain C static constant initializers
      tables.h     ( rootname2.h ) contains extern declarations

   Version 1.5 - /j. Swan 02/28/03 - updated 2d and 3d ouptut 
                 resolution to 8 digits: 
     
************************************************************* */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define MAXLINE 256
#define MAXPOINTS 10000
#define MAXNAME 32
#define MAXTABLES 2000


typedef struct {
  char name[MAXNAME];
  float xdata[MAXPOINTS];   /* array of 'x' values */
  float ydata[MAXPOINTS];   /* array of 'y' values */
  float zdata[MAXPOINTS];   /* array of 'z' values */
  float sx;                 /* scalar on 'X' data */
  float ax;                 /* adder  on 'X' data */
  float sy;                 /* scalar on 'Y' data */
  float ay;                 /* adder  on 'Y' data */
  float sz;                 /* scalar on 'Z' data */
  float az;                 /* adder  on 'Z' data */
  int x_index;              /* index of 'x' data array */
  int y_index;              /* index of 'y' data array */
  int z_index;              /* index of 'z' data array */
} TABLE;

typedef struct {
  char name[MAXNAME];
  float wdata[MAXPOINTS];   /* array of 'w' values */
  char* sdata[MAXPOINTS];   /* array of 's' values */
  int w_index;              /* index of 'w' data array */
  int s_index;              /* index of 's' data array */
} TABLEA;


int main(argc,argv)
     int argc;
     char *argv[];
{
  FILE *ptr_in_fn;
  FILE *ptr_out_fn;
  FILE *ptr_out_fn_3;

  TABLE *tbl[MAXTABLES];
  int num_tbl;

  TABLEA *tbla[MAXTABLES];
  int num_tbla;

  char line[MAXLINE];
  char *got;
  int numr;

  char input[MAXLINE];
  char tblid[MAXLINE];
  int i, n, end, whatdata;

  char axis[MAXNAME];
  static char XAXIS[MAXNAME] = {"X"};
  static char YAXIS[MAXNAME] = {"Y"};
  static char ZAXIS[MAXNAME] = {"Z"};
  static char WAXIS[MAXNAME] = {"W"};
  static char SAXIS[MAXNAME] = {"S"};
  static char SX[MAXNAME] = {"SX"};
  static char AX[MAXNAME] = {"AX"};
  static char SY[MAXNAME] = {"SY"};
  static char AY[MAXNAME] = {"AY"};
  static char SZ[MAXNAME] = {"SZ"};
  static char AZ[MAXNAME] = {"AZ"};
  char buffer[MAXLINE];
  char out_file[MAXNAME];
  char fn_2[MAXNAME];
  char fn_3[MAXNAME];
  int in_number, in_name;

  /* ---------------------------------------------------------------------- */

  if (argc < 2) {
    printf("\nTo run enter:f3_ctblmkr [in-file]\n");
    goto ERROR_EXIT;
  }

   (void)strcpy(out_file,"tables_def.h" );
   (void)strcpy(fn_2,"tables.h"); 
   (void)strcpy(fn_3,"general_ram.tbl"); 

  printf("\n f3_ctblmkr: Input  file: %s",argv[1]);
  printf("\n f3_ctblmkr: Output file: %s",out_file);
  printf("\n f3_ctblmkr: Output file: %s",fn_2);
  printf("\n f3_ctblmkr: Output file: %s\n",fn_3);

  ptr_in_fn = fopen(argv[1], "r");
  if(ptr_in_fn == NULL) {
    printf("\nf3_ctblmkr, ERROR: Cannot open: %s\n",argv[1]);
     exit(-1);
  }
  ptr_out_fn = fopen(out_file, "w");
  if(ptr_out_fn == NULL) {
    printf("\nf3_ctblmkr, ERROR: Cannot open: %s\n",out_file);
     exit(-1);
  }
  ptr_out_fn_3 = fopen(fn_3, "w");
  if(ptr_out_fn_3 == NULL) {
    printf("\nf3_ctblmkr, ERROR: Cannot open: %s\n",fn_3);
     exit(-1);
  }


  num_tbl = -1;
  num_tbla = -1;

  do /* Look for start of table */ {

    got = fgets(line, MAXLINE, ptr_in_fn);
    if (got == NULL)
      continue;

    numr = sscanf(line,"%s %*[TA] %*[= \'] %[^ \']",input,tblid);
    if (numr != 2)
      continue;

    /*========================================================================*/
    /* Process a 2-D or 3-D table */

    if (strcmp(input,"$INPUT") == 0) {
      /* Increment table index and allocate memory for structure */
      num_tbl = num_tbl + 1 ;
      if (num_tbl>MAXTABLES-1) {
	printf("\nf3_ctblmkr, ERROR: Exceeded allowable number of tables: MAXTABLES\n");
	goto ERROR_EXIT;
      }
      tbl[num_tbl] = (TABLE *)calloc(1,sizeof(TABLE));
     
      got = fgets(line, MAXLINE, ptr_in_fn);  /* initalize loop */
      strcpy(tbl[num_tbl]->name,tblid);
      tbl[num_tbl]->x_index = -1;
      tbl[num_tbl]->y_index = -1;
      tbl[num_tbl]->z_index = -1;
      tbl[num_tbl]->sx = 1.0;
      tbl[num_tbl]->ax = 0.0;
      tbl[num_tbl]->sy = 1.0;
      tbl[num_tbl]->ay = 0.0;
      tbl[num_tbl]->sz = 1.0;
      tbl[num_tbl]->az = 0.0;

      end = 0;
      i = -1;
      n = -1;
      in_number = 0;

      do /* process table data */ {
	n = n + 1;
          
	if( line[n] == '1' || line[n] == '2' || line[n] == '3' || 
	    line[n] == '4' || line[n] == '5' || line[n] == '6' || 
	    line[n] == '7' || line[n] == '8' || line[n] == '9' || 
	    line[n] == '0' || line[n] == '.' || line[n] == '-' ||
	    line[n] == 'E' || line[n] == 'e' || line[n] == '+' ) {
	  buffer[++i] = line[n];
	  in_number = 1;
	}
	else if(in_number==1 &&
		(line[n]==',' || line[n]=='\n' || line[n]==' ' ||
		 line[n]=='\t' || line[n]==NULL)) {
	  /* store data value */
	  in_number = 0;
	  buffer[i+1] = NULL;
	  switch( whatdata ) {
	  case 1 :
	    if (tbl[num_tbl]->x_index >= MAXPOINTS-2) {
	      printf("\nf3_ctblmkr, ERROR: number of X points > MAXPOINTS\n");
	      goto ERROR_EXIT;
	    }
	    tbl[num_tbl]->x_index = tbl[num_tbl]->x_index + 1;
	    sscanf(buffer,"%f",
		   &(tbl[num_tbl]->xdata[ tbl[num_tbl]->x_index ]) );
	    break;
	  case 2 : 
	    if (tbl[num_tbl]->y_index >= MAXPOINTS-2) {
	      printf("\nf3_ctblmkr, ERROR: number of Y points > MAXPOINTS\n");
	      goto ERROR_EXIT;
	    }
	    tbl[num_tbl]->y_index = tbl[num_tbl]->y_index + 1;
	    sscanf(buffer,"%f",
		   &(tbl[num_tbl]->ydata[ tbl[num_tbl]->y_index ]) );
	    break;
	  case 3 : 
	    if (tbl[num_tbl]->z_index >= MAXPOINTS-2) {
	      printf("\nf3_ctblmkr, ERROR: number of Z points > MAXPOINTS\n");
	      goto ERROR_EXIT;
	    }
	    tbl[num_tbl]->z_index = tbl[num_tbl]->z_index + 1;
	    sscanf(buffer,"%f",
		   &(tbl[num_tbl]->zdata[ tbl[num_tbl]->z_index ]) );
	    break; 
	  case 4 : 
	    sscanf(buffer,"%f", &(tbl[num_tbl]->sx) );
	    break; 
	  case 5 : 
	    sscanf(buffer,"%f", &(tbl[num_tbl]->ax) );
	    break;
	  case 6 :
	    sscanf(buffer,"%f", &(tbl[num_tbl]->sy) );
	    break;
	  case 7 :
	    sscanf(buffer,"%f", &(tbl[num_tbl]->ay) );
	    break;
	  case 8 : 
	    sscanf(buffer,"%f", &(tbl[num_tbl]->sz) );
	    break;
	  case 9 :
	    sscanf(buffer,"%f", &(tbl[num_tbl]->az) );
	    break;
	  default: printf("\nf3_ctblmkr, ERROR: case error\n");  
	    goto ERROR_EXIT;
	  }
	  i = -1;
	  if(line[n] == '\n' ) {
	    /* printf("\nline[%d]=>is new line\n",n,line[n]); */
	    n = -1;
	    got = fgets(line, MAXLINE, ptr_in_fn);
	  }
	}
	else if(line[n] == 'X' || line[n] == 'Y' || line[n] == 'Z' 
		|| line[n] == 'A' || line[n] == 'S') {
	  buffer[++i] = line[n];
	}
	else if(line[n] == '=' ) { /* determine "whatdata" is to follow */
	  buffer[i+1] = NULL;

	  numr = sscanf(buffer," %[XYZAS] %*[ =]", axis);
	  whatdata = -1;
	  if ( strcmp(axis,XAXIS) == 0){whatdata = 1;}
	  if ( strcmp(axis,YAXIS) == 0){whatdata = 2;}
	  if ( strcmp(axis,ZAXIS) == 0){whatdata = 3;}
	  if ( strcmp(axis,SX) == 0){whatdata = 4;}
	  if ( strcmp(axis,AX) == 0){whatdata = 5;}
	  if ( strcmp(axis,SY) == 0){whatdata = 6;}
	  if ( strcmp(axis,AY) == 0){whatdata = 7;}
	  if ( strcmp(axis,SZ) == 0){whatdata = 8;}
	  if ( strcmp(axis,AZ) == 0){whatdata = 9;}
	  if ( whatdata == -1) {
	    printf("\nf3_ctblmkr, ERROR: whatdata\n%s\n",line);
	    goto ERROR_EXIT;
	  }
	  i = -1;
	}
	else if(line[n] == '\n' ) {
	  /* printf("\nline[%d]=>is new line\n",n,line[n]); */
	  n = -1;
	  got = fgets(line, MAXLINE, ptr_in_fn);
	}
	else if(line[n] == '$' ) {
	  end = 1;
	}
	else if(line[n] == ' ' || line[n] == '\t' || line[n] == ',' ) {
	  /* skip spaces, tabs, and commas */
	}
	else {
	  printf("\nf3_ctblmkr, ERROR: Processing a table, LOST in if\n");
	  printf("tbl[%d].name: %s\n",num_tbl,tbl[num_tbl]->name);
	  printf("line=>%s\n",line);
	  if(line[n] == NULL )
	    printf("line[%d]=NULL\n",n);
	  else
	    printf("line[%d]='%c'\n",n,line[n]);
	  goto ERROR_EXIT;
	}
      } while (end == 0);  /* process table data */

    } /* if, Found a 2-D or 3-D table */

    /*========================================================================*/
    /* Process a 4-D table */
    else if (strcmp(input,"$INPUTA") == 0) {

      /* Increment table index and allocate memory for structure */
      num_tbla = num_tbla + 1 ;
      if (num_tbla>MAXTABLES-1) {
	printf("\nf3_ctblmkr, ERROR: Exceeded allowable number of 4-D tables: MAXTABLES\n");
	goto ERROR_EXIT;
      }
      tbla[num_tbla] = (TABLEA *)calloc(1,sizeof(TABLEA));
     
      got = fgets(line, MAXLINE, ptr_in_fn);  /* initalize loop */
      strcpy(tbla[num_tbla]->name,tblid);
      tbla[num_tbla]->w_index = -1;
      tbla[num_tbla]->s_index = -1;

      end = 0;
      i = -1;
      n = -1;
      in_number = 0;
      in_name = 0;
      whatdata = -1;

      do /* process table data */ {
	n = n + 1;

	if (whatdata == 2 && line[n] == '\'') {
	  if (! in_name) {
	    in_name = 1;
	    i = -1;
	  }
	  else {
	    in_name = 0;
	    buffer[i+1] = NULL;
	    i = -1;
	    if (tbla[num_tbla]->s_index >= MAXPOINTS-2) {
	      printf("\nf3_ctblmkr, ERROR: number of S points > MAXPOINTS\n");
	      goto ERROR_EXIT;
	    }
	    tbla[num_tbla]->s_index++;
	    tbla[num_tbla]->sdata[ tbla[num_tbla]->s_index ] = strdup(buffer);
	    /* printf("tbla[%d] sdata[%d] = %s\n", num_tbla,
		   tbla[num_tbla]->s_index,
		   tbla[num_tbla]->sdata[ tbla[num_tbla]->s_index ]); */
	  }
	}
	else if (in_name && (isalnum(line[n]) || line[n] == '_')) {
	  buffer[++i] = line[n];
	}
	else if( line[n] == '1' || line[n] == '2' || line[n] == '3' || 
	    line[n] == '4' || line[n] == '5' || line[n] == '6' || 
	    line[n] == '7' || line[n] == '8' || line[n] == '9' || 
	    line[n] == '0' || line[n] == '.' || line[n] == '-' ||
	    line[n] == 'E' || line[n] == 'e' || line[n] == '+' ) {
	  buffer[++i] = line[n];
	  in_number = 1;
	}
	else if(line[n] == 'W' || line[n] == 'S') {
	  buffer[++i] = line[n];
	}
	else if(line[n] == '=' ) { /* determine "whatdata" is to follow */
	  buffer[i+1] = NULL;
	  in_number = 0;
	  in_name = 0;
	  numr = sscanf(buffer," %s", axis);
	  whatdata = -1;
	  if ( strcmp(axis,WAXIS) == 0){whatdata = 1;}
	  if ( strcmp(axis,SAXIS) == 0){whatdata = 2;}
	  if ( whatdata == -1) {
	    printf("\nf3_ctblmkr, ERROR: 4-D whatdata\n%s\n",line);
	    goto ERROR_EXIT;
	  }
	  i = -1;           
	}
	else if(in_number==1 &&
		(line[n]==',' || line[n]=='\n' || line[n]==' ' ||
		 line[n]=='\t' || line[n]=='\'' || line[n]==NULL)) {
	  /* store data value */
	  in_number = 0;
	  buffer[i+1] = NULL;
	  switch( whatdata ) {
	  case 1 :
	    if (tbla[num_tbla]->w_index >= MAXPOINTS-2) {
	      printf("\nf3_ctblmkr, ERROR: number of W points > MAXPOINTS\n");
	      goto ERROR_EXIT;
	    }
	    tbla[num_tbla]->w_index++;
	    sscanf(buffer,"%f",
		   &(tbla[num_tbla]->wdata[ tbla[num_tbla]->w_index ]) );
	    /* printf("tbla[%d] wdata[%d] = %f\n", num_tbla,
		   tbla[num_tbla]->w_index,
		   tbla[num_tbla]->wdata[ tbla[num_tbla]->w_index ]); */
	    break;

	  default: printf("\nf3_ctblmkr, ERROR: 4-D case error\n");  
	    goto ERROR_EXIT;
	  }
	  i = -1;
	  if(line[n] == '\n' ) {
	    /* printf("\nline[%d]=>is new line\n",n,line[n]); */
	    n = -1;
	    got = fgets(line, MAXLINE, ptr_in_fn);
	  }
	}
	else if(line[n] == '\n' ) {
	  /* printf("\nline[%d]=>is new line\n",n,line[n]); */
	  n = -1;
	  got = fgets(line, MAXLINE, ptr_in_fn);
	}
	else if(line[n] == '$' ) {
	  end = 1;
	}
	else if(line[n] == ' ' || line[n] == '\t' || line[n] == ',' ) {
	  /* skip spaces, tabs, and commas */
	}
	else {
	  printf("\nf3_ctblmkr, ERROR: Processing a 4-D table, LOST in if\n");
	  printf("tbla[%d].name: %s\n",num_tbla,tbla[num_tbla]->name);
	  printf("line=>%s\n",line);
	  if(line[n] == NULL )
	    printf("line[%d]=NULL\n",n);
	  else
	    printf("line[%d]='%c'\n",n,line[n]);
	  goto ERROR_EXIT;
	}
      } while (end == 0);  /* process table data */
    } /* if, Found a 4-D (W-S) table */

  } while (got != NULL); /* Look for start of table  */
  (void)fclose(ptr_in_fn);   /* close input data file */

  /* 2d table: length of z array    = tbl[n]->x_index + 1  */
  /*           tbl array size       = num of points  + 1   */
  /*           add 1 cause tbl[0].x = length of z array    */

  fprintf(ptr_out_fn,"#include \"be_tbls.h\"\n");
  fprintf(ptr_out_fn,"#include \"AS_GLOBALS.h\"\n");
  for ( n=0; n <=num_tbl; ++n ) {
    if ( tbl[n]->y_index == -1) { /* Then its a 2d table */
      /* Check that the X array and Z array are the same size. */
      if ( tbl[n]->x_index != tbl[n]->z_index ) {
	printf("\nf3_ctblmkr, ERROR: %s : number x != number z",tbl[n]->name );
	printf("\nf3_ctblmkr, ERROR: number x = %d", tbl[n]->x_index + 1);
	printf("\nf3_ctblmkr, ERROR: number z = %d\n", tbl[n]->z_index + 1);
	goto ERROR_EXIT;
      }

      fprintf(ptr_out_fn,"\nconst FLT_univariate_table_point %s[%d] = {\n",
	      tbl[n]->name,tbl[n]->x_index + 2);
      /* zeroth set of points, x  = length of z array */
      fprintf( ptr_out_fn, "{%f,0.0},\n", (float)(tbl[n]->x_index + 1) );
      for ( i=0; i <= tbl[n]->x_index ; ++i )
	{ fprintf( ptr_out_fn,"{%f,%.8f},\n",
		   (tbl[n]->xdata[i])*tbl[n]->sx + tbl[n]->ax ,
		   (tbl[n]->zdata[i])*tbl[n]->sz + tbl[n]->az );}
      fprintf(ptr_out_fn,"};\n");
    }
    else { /* Then its a 3d table */
      /* Check that (size of X)*(size of Y) = (size of Z). */
      if ( (tbl[n]->x_index + 1)*(tbl[n]->y_index + 1) 
	   != (tbl[n]->z_index + 1) ) {
	printf("\nf3_ctblmkr, ERROR: %s : number x*y != number z",tbl[n]->name );
	printf("\nf3_ctblmkr, ERROR: number x = %d", tbl[n]->x_index + 1);
	printf("\nf3_ctblmkr, ERROR: number y = %d", tbl[n]->y_index + 1);
	printf("\nf3_ctblmkr, ERROR: number z = %d\n", tbl[n]->z_index + 1);
	goto ERROR_EXIT;
      }

      /* x */
      fprintf(ptr_out_fn,"\nconst float32 %s_X[%d] = {\n",
	      tbl[n]->name,tbl[n]->x_index + 2);
      /* zeroth set of points, x  = length of z array */
      fprintf( ptr_out_fn, "%f,\n", (float)(tbl[n]->x_index + 1) );
      for ( i=0; i <= tbl[n]->x_index ; ++i )
	{ fprintf( ptr_out_fn,"%.8f,\n",
		   (tbl[n]->xdata[i])*tbl[n]->sx + tbl[n]->ax ); }
      fprintf(ptr_out_fn,"};\n");
      /* y */
      fprintf(ptr_out_fn,"\nconst float32 %s_Y[%d] = {\n",
	      tbl[n]->name,tbl[n]->y_index + 2);
      /* zeroth set of points, y  = length of y array */
      fprintf( ptr_out_fn, "%f,\n", (float)(tbl[n]->y_index + 1) );
      for ( i=0; i <= tbl[n]->y_index ; ++i )
	{ fprintf( ptr_out_fn,"%.8f,\n",
		   (tbl[n]->ydata[i])*tbl[n]->sy + tbl[n]->ay ); }
      fprintf(ptr_out_fn,"};\n");
      /* z */
      fprintf(ptr_out_fn,"\nconst float32 %s_Z[%d] = {\n",
	      tbl[n]->name,tbl[n]->z_index + 2);
      /* zeroth set of points, z  = length of z array */
      fprintf( ptr_out_fn, "%f,\n", (float)(tbl[n]->z_index + 1) );
      for ( i=0; i <= tbl[n]->z_index ; ++i )
	{ fprintf( ptr_out_fn,"%.8f,\n",
		   (tbl[n]->zdata[i])*tbl[n]->sz + tbl[n]->az ); }
      fprintf(ptr_out_fn,"};\n");
    }
  }

  /* Write declarations of 4-D tables with initializers.
     These are written after all of the 3-D tables because the 4-D tables
     contain addresses of the 3-D tables. */
  for ( n=0; n <=num_tbla; ++n ) {
    /* Check that the W array and S array are the same size. */
    if ( tbla[n]->w_index != tbla[n]->s_index ) {
      printf("\nf3_ctblmkr, ERROR: %s : number W != number S", tbla[n]->name);
      printf("\nf3_ctblmkr, ERROR: number W = %d", tbla[n]->w_index + 1);
      printf("\nf3_ctblmkr, ERROR: number S = %d\n", tbla[n]->s_index + 1);
      goto ERROR_EXIT;
    }
    /* Create root name with modified prefix for static indices. */
    strcpy(buffer, tbla[n]->name);
    buffer[1] = 'V'; /* change second letter of prefix from 'T' to 'V' */
    fprintf(ptr_out_fn_3,"extern int16 %sWPTR;\n", buffer);
    fprintf(ptr_out_fn_3,"extern int16 %sXPTR;\n", buffer);
    fprintf(ptr_out_fn_3,"extern int16 %sYPTR;\n",buffer);

    fprintf(ptr_out_fn,"const FLT_4D_table_point %s[%d] = {\n",
	    tbla[n]->name, tbla[n]->w_index + 2);

    fprintf(ptr_out_fn,"  { %f, &%sWPTR, &%sXPTR, &%sYPTR },\n",
	    (float)(tbla[n]->w_index+1), buffer, buffer, buffer);

    for ( i=0; i <= tbla[n]->w_index ; ++i ) {
      char *name = tbla[n]->sdata[i];
      fprintf(ptr_out_fn, "  { %f, &%s_X, &%s_Y, &%s_Z },\n",
	      tbla[n]->wdata[i], name, name, name);
    }
    fprintf(ptr_out_fn, "};\n");
  }

  (void)fclose(ptr_out_fn);  /* close output data file */

  ptr_out_fn = fopen(fn_2, "w");
  if(ptr_out_fn == NULL) {
    printf("\nf3_ctblmkr, ERROR: Cannot open: %s\n",fn_2);
     exit(-1);
  }
  /* Arrays are NOT declared "const" here because this conflicts with
     BEACON-generated extern declaration in the C modules. */

  fprintf(ptr_out_fn,"#ifndef _TABLES_H\n");
  fprintf(ptr_out_fn,"#define _TABLES_H\n");

  fprintf(ptr_out_fn,"#include \"be_tbls.h\"\n");
  for ( n=0; n <=num_tbl; ++n ) {
    if ( tbl[n]->y_index == -1) { /* Then its a 2d table */
      fprintf(ptr_out_fn,"extern FLT_univariate_table_point %s[%d];\n",
	      tbl[n]->name,tbl[n]->x_index + 2);
    }
    else { /* Then its a 3d table */
      /* x */
      fprintf(ptr_out_fn,"extern float32 %s_X[%d];\n",
	      tbl[n]->name, tbl[n]->x_index + 2);
      /* y */
      fprintf(ptr_out_fn,"extern float32 %s_Y[%d];\n",
	      tbl[n]->name, tbl[n]->y_index + 2);
      /* z */
      fprintf(ptr_out_fn,"extern float32 %s_Z[%d];\n",
	      tbl[n]->name, tbl[n]->z_index + 2);
    }
  }
  /* Write external declarations of 4-D tables. */
  for ( n=0; n <=num_tbla; ++n ) {
    fprintf(ptr_out_fn,"extern const FLT_4D_table_point %s[%d];\n",
	    tbla[n]->name, tbla[n]->w_index + 2);
  }
  fprintf(ptr_out_fn,"#endif\n");

  fclose(ptr_out_fn);  /* close output data file */
  exit(0);

ERROR_EXIT:
  (void)fclose(ptr_in_fn);   /* close input data file */
  (void)fclose(ptr_out_fn);  /* close output data file */
  (void)fclose(ptr_out_fn_3);  /* close output data file */
  (void)unlink(out_file);
  exit(-1);
}
