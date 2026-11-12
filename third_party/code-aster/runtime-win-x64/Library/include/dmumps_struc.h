!
!  This file is part of MUMPS 5.8.2, released
!  on Mon Jan 12 15:17:08 UTC 2026
!
!
!  Copyright 1991-2026 CERFACS, CNRS, ENS Lyon, INP Toulouse, Inria,
!  Mumps Technologies, University of Bordeaux.
!
!  This version of MUMPS is provided to you free of charge. It is
!  released under the CeCILL-C license 
!  (see doc/CeCILL-C_V1-en.txt, doc/CeCILL-C_V1-fr.txt, and
!  https://cecill.info/licences/Licence_CeCILL-C_V1-en.html)
!
      TYPE DMUMPS_STRUC
        SEQUENCE
!
! This structure contains all parameters 
! for the interface to the user, plus internal
! information from the solver
!
! *****************
! INPUT PARAMETERS
! *****************
!    -----------------
!    MPI Communicator
!    -----------------
        INTEGER(4) :: COMM
!    ------------------
!    Problem definition
!    ------------------
!    Solver (SYM=0 unsymmetric,SYM=1 symmetric Positive Definite, 
!        SYM=2 general symmetric)
!    Type of parallelism (PAR=1 host working, PAR=0 host not working)
        INTEGER(4) ::  SYM, PAR
        INTEGER(4) ::  JOB 
!    --------------------
!    Order of Input matrix 
!    --------------------
        INTEGER(4) ::  N
!
!    ----------------------------------------
!    Assembled input matrix : User interface
!    ----------------------------------------
        INTEGER(4) :: NZ  ! Standard integer input + bwd. compat.
        INTEGER(8) :: NNZ ! 64-bit integer input
        DOUBLE PRECISION, DIMENSION(:), POINTER :: A
        INTEGER(4), DIMENSION(:), POINTER :: IRN, JCN
!    --------------
!    Scaling arrays
!    --------------
        DOUBLE PRECISION, DIMENSION(:), POINTER :: COLSCA, ROWSCA
        DOUBLE PRECISION, DIMENSION(:), POINTER :: COLSCA_loc
        DOUBLE PRECISION, DIMENSION(:), POINTER :: ROWSCA_loc
        INTEGER(4), DIMENSION(:), POINTER :: ROWIND, COLIND
        DOUBLE PRECISION, DIMENSION(:), POINTER :: PIVOTS
!
!       ------------------------------------
!       Case of distributed assembled matrix
!       matrix on entry:
!       ------------------------------------
        INTEGER(4) :: NZ_loc  ! Standard integer input + bwd. compat.
        INTEGER(4) :: pad1
        INTEGER(8) :: NNZ_loc ! 64-bit integer input
        INTEGER(4), DIMENSION(:), POINTER :: IRN_loc, JCN_loc
        DOUBLE PRECISION, DIMENSION(:), POINTER :: A_loc, pad2
!
!    ----------------------------------------
!    Unassembled input matrix: User interface
!    ----------------------------------------
        INTEGER(4) :: NELT, pad3
        INTEGER(4), DIMENSION(:), POINTER :: ELTPTR
        INTEGER(4), DIMENSION(:), POINTER :: ELTVAR
        DOUBLE PRECISION, DIMENSION(:), POINTER :: A_ELT, pad4
!
!    ---------------------------------------------
!    Symmetric permutation : 
!               PERM_IN if given by user (optional)
!    ---------------------------------------------
        INTEGER(4), DIMENSION(:), POINTER :: PERM_IN
!
!    ----------------
!    Format by blocks
!    ----------------
        INTEGER(4) :: NBLK, pad5
        INTEGER(4), DIMENSION(:), POINTER :: BLKPTR
        INTEGER(4), DIMENSION(:), POINTER :: BLKVAR
!
! ******************
! INPUT/OUTPUT data 
! ******************
!    --------------------------------------------------------
!    RHS / SOL_loc
!    -------------
!       right-hand side and solution
!    -------------------------------------------------------
        DOUBLE PRECISION, DIMENSION(:), POINTER :: RHS, REDRHS
        DOUBLE PRECISION, DIMENSION(:), POINTER :: RHS_SPARSE
        DOUBLE PRECISION, DIMENSION(:), POINTER :: SOL_loc
        DOUBLE PRECISION, DIMENSION(:), POINTER :: RHS_loc
        INTEGER(4), DIMENSION(:), POINTER :: IRHS_SPARSE
        INTEGER(4), DIMENSION(:), POINTER :: IRHS_PTR
        INTEGER(4), DIMENSION(:), POINTER :: ISOL_loc
        INTEGER(4), DIMENSION(:), POINTER :: IRHS_loc
        INTEGER(4) :: LRHS, NRHS, NZ_RHS, Nloc_RHS, LRHS_loc, LREDRHS
        INTEGER(4) :: LSOL_loc, NSOL_loc
        INTEGER(4) :: LD_RHSINTR, pad6
!    ----------------------------
!    Control parameters,
!    statistics and output data
!    ---------------------------
        INTEGER(4) ::  ICNTL(60)
        INTEGER(4) ::  INFO(80) 
        INTEGER(4) :: INFOG(80)
        DOUBLE PRECISION ::  COST_SUBTREES
        DOUBLE PRECISION ::  CNTL(15)
        DOUBLE PRECISION ::  RINFO(40)
        DOUBLE PRECISION ::  RINFOG(40)
! The options array for metis/parmetis
        INTEGER(4) ::  METIS_OPTIONS(40)
!    ---------------------------------------------------------
!    Permutations computed during analysis:
!       SYM_PERM: Symmetric permutation 
!       UNS_PERM: Column permutation (optional)
!    ---------------------------------------------------------
        INTEGER(4), DIMENSION(:), POINTER :: SYM_PERM, UNS_PERM
! 
!    -----
!    Schur
!    -----
        INTEGER(4) ::  NPROW, NPCOL, MBLOCK, NBLOCK
        INTEGER(4) ::  SCHUR_MLOC, SCHUR_NLOC, SCHUR_LLD
        INTEGER(4) ::  SIZE_SCHUR
        DOUBLE PRECISION, DIMENSION(:), POINTER :: SCHUR
        DOUBLE PRECISION, DIMENSION(:), POINTER :: SCHUR_CINTERFACE
        INTEGER(4), DIMENSION(:), POINTER :: LISTVAR_SCHUR
!    -------------------------------------
!    Case of distributed matrix on entry:
!    DMUMPS potentially provides mapping
!    -------------------------------------
        INTEGER(4), DIMENSION(:), POINTER :: MAPPING
!    --------------
!    Version number
!    --------------
        CHARACTER(LEN=30) ::  VERSION_NUMBER
!    -----------
!    Out-of-core
!    -----------
        CHARACTER(LEN=1023) :: OOC_TMPDIR
        CHARACTER(LEN=255) :: OOC_PREFIX
!    ------------------------------------------
!    Name of file to dump a matrix/rhs to disk
!    ------------------------------------------
        CHARACTER(LEN=1023) ::  WRITE_PROBLEM
!    -----------
!    Save/Restore
!    -----------
        CHARACTER(LEN=1023) :: SAVE_DIR
        CHARACTER(LEN=255)  :: SAVE_PREFIX
        CHARACTER(LEN=7)   ::  pad7  
!
!
! **********************
! INTERNAL Working data
! *********************
        INTEGER(8) :: KEEP8(150), MAX_SURF_MASTER
        INTEGER(4) ::  INST_Number
!       For MPI
        INTEGER(4) ::  COMM_NODES, MYID_NODES, COMM_LOAD
        INTEGER(4) ::  MYID, NPROCS, NSLAVES
        INTEGER(4) ::  ASS_IRECV
!       IS is used for the factors + workspace for contrib. blocks
        INTEGER(4), DIMENSION(:), POINTER :: IS
        INTEGER(4) ::  KEEP(500)
!       The following data/arrays are computed during the analysis
!       phase and used during the factorization and solve phases.
        INTEGER(4) ::  LNA
        INTEGER(4) ::  NBSA
        INTEGER(4),POINTER,DIMENSION(:) :: STEP, NE_STEPS, ND_STEPS
        INTEGER(4),POINTER,DIMENSION(:) :: FRERE_STEPS, DAD_STEPS
        INTEGER(4),POINTER,DIMENSION(:) :: FILS, FRTPTR, FRTELT
        INTEGER(8),POINTER,DIMENSION(:) :: PTRAR, PTR8ARR
        INTEGER(4),POINTER,DIMENSION(:) :: NINCOLARR,NINROWARR,PTRDEBARR
        INTEGER(4),POINTER,DIMENSION(:) :: NA, PROCNODE_STEPS
!       Info for pruning tree 
        INTEGER(4),POINTER,DIMENSION(:) :: Step2node
!       PTLUST_S and PTRFAC are two pointer arrays computed during
!       factorization and used by the solve
        INTEGER(4), DIMENSION(:), POINTER :: PTLUST_S
        INTEGER(8), DIMENSION(:), POINTER :: PTRFAC
!       main real working arrays for factorization/solve phases
        DOUBLE PRECISION, DIMENSION(:), POINTER :: S
        REAL(kind(0.E0)), DIMENSION(:), POINTER :: LPS
!       Information on mapping
        INTEGER(4), DIMENSION(:), POINTER :: PROCNODE
!       Input matrix ready for numerical assembly 
!           -arrowhead format in case of assembled matrix
!           -element format otherwise
!       Element entry: internal data
        INTEGER(4) :: NELT_loc, LELTVAR
        INTEGER(4), DIMENSION(:), POINTER :: ELTPROC
!       Candidates and node partitionning
        INTEGER(4), DIMENSION(:,:), POINTER :: CANDIDATES
        INTEGER(4), DIMENSION(:),   POINTER :: ISTEP_TO_INIV2
        INTEGER(4), DIMENSION(:),   POINTER :: FUTURE_NIV2
        INTEGER(4), DIMENSION(:,:), POINTER :: TAB_POS_IN_PERE 
        LOGICAL(4), DIMENSION(:),   POINTER :: I_AM_CAND
!       For heterogeneous architecture
        INTEGER(4), DIMENSION(:), POINTER :: MEM_DIST
!       Compressed RHS
        INTEGER(4), DIMENSION(:),   POINTER :: GLOB2LOC_RHS
        LOGICAL(4) :: GLOB2LOC_SOL_ALLOC, pad11
        INTEGER(4), DIMENSION(:),   POINTER :: GLOB2LOC_SOL
        DOUBLE PRECISION, DIMENSION(:),   POINTER :: RHSINTR
!       Info on the subtrees to be used during factorization
        DOUBLE PRECISION, DIMENSION(:), POINTER :: MEM_SUBTREE
        DOUBLE PRECISION, DIMENSION(:), POINTER :: COST_TRAV
        INTEGER(4), DIMENSION(:),   POINTER :: MY_ROOT_SBTR
        INTEGER(4), DIMENSION(:),   POINTER :: MY_FIRST_LEAF
        INTEGER(4), DIMENSION(:),   POINTER :: MY_NB_LEAF
        INTEGER(4), DIMENSION(:),   POINTER :: DEPTH_FIRST
        INTEGER(4), DIMENSION(:),   POINTER :: DEPTH_FIRST_SEQ
        INTEGER(4), DIMENSION(:),   POINTER :: SBTR_ID
        INTEGER(4), DIMENSION(:),   POINTER :: SCHED_DEP
        INTEGER(4), DIMENSION(:),   POINTER :: SCHED_GRP
        INTEGER(4), DIMENSION(:),   POINTER :: SCHED_SBTR
        INTEGER(4), DIMENSION(:),   POINTER :: CROIX_MANU
        DOUBLE PRECISION, DIMENSION(:),   POINTER :: WK_USER
        INTEGER(4) :: NBSA_LOCAL
        INTEGER(4) :: LWK_USER
!    Internal control array
        DOUBLE PRECISION ::  DKEEP(230)
!    For simulating parallel out-of-core stack.
        DOUBLE PRECISION, DIMENSION(:),POINTER :: CB_SON_SIZE
!    Instance number used/managed by the C/F77 interface
        INTEGER(4) ::  INSTANCE_NUMBER
!    OOC management data that must persist from factorization to solve.
        INTEGER(4) ::  OOC_MAX_NB_NODES_FOR_ZONE
        INTEGER(4), DIMENSION(:,:),   POINTER :: OOC_INODE_SEQUENCE
        INTEGER(8),DIMENSION(:,:), POINTER :: OOC_SIZE_OF_BLOCK
        INTEGER(8), DIMENSION(:,:),   POINTER :: OOC_VADDR
        INTEGER(4),DIMENSION(:), POINTER :: OOC_TOTAL_NB_NODES
        INTEGER(4),DIMENSION(:), POINTER :: OOC_NB_FILES
        INTEGER(4) :: OOC_NB_FILE_TYPE,pad12
        INTEGER(4),DIMENSION(:), POINTER :: OOC_FILE_NAME_LENGTH
        CHARACTER,DIMENSION(:,:), POINTER :: OOC_FILE_NAMES  
!    Indices of nul pivots
        INTEGER(4),DIMENSION(:), POINTER :: PIVNUL_LIST
!    Array needed to manage additionnal candidate processor 
        INTEGER(4), DIMENSION(:,:), POINTER :: SUP_PROC, pad14
!    Lists of nodes where processors work. Built/used in solve phase.
        INTEGER(4), DIMENSION(:), POINTER :: IPTR_WORKING, WORKING
!    Internal data structures accessor
        CHARACTER, DIMENSION(:), POINTER :: INTR_ENCODING
!    Low-rank
        INTEGER(4), POINTER, DIMENSION(:) :: LRGROUPS
        INTEGER(4) :: NBGRP,pad13
!    Pointer encoding for FDM_F data
        CHARACTER, DIMENSION(:), POINTER :: FDM_F_ENCODING
!    Pointer array encoding BLR factors pointers
        CHARACTER, DIMENSION(:), POINTER :: BLRARRAY_ENCODING
!    Multicore
        INTEGER(4) :: LPOOL_A_L0_OMP, LPOOL_B_L0_OMP
        INTEGER(4) :: L_PHYS_L0_OMP
        INTEGER(4) :: L_VIRT_L0_OMP
        INTEGER(4) :: LL0_OMP_MAPPING, LL0_OMP_FACTORS
        INTEGER(8) :: THREAD_LA
! Estimates before L0_OMP
        INTEGER(4), DIMENSION(:,:), POINTER    :: I4_L0_OMP
        INTEGER(8), DIMENSION(:,:), POINTER :: I8_L0_OMP
! Pool before L0_OMP
        INTEGER(4), DIMENSION(:), POINTER :: IPOOL_B_L0_OMP
! Pool after L0_OMP
        INTEGER(4), DIMENSION(:), POINTER :: IPOOL_A_L0_OMP
! Subtrees
        INTEGER(4), DIMENSION(:), POINTER :: PHYS_L0_OMP
! Amalgamated subtrees
        INTEGER(4), DIMENSION(:), POINTER :: VIRT_L0_OMP
! Mapping of amalgamated subtrees
        INTEGER(4), DIMENSION(:), POINTER :: VIRT_L0_OMP_MAPPING
! From heaviest to lowest subtree
        INTEGER(4), DIMENSION(:), POINTER :: PERM_L0_OMP
! To get leafs in global pool
        INTEGER(4), DIMENSION(:), POINTER :: PTR_LEAFS_L0_OMP
! Mapping of the subtree nodes
        INTEGER(4), DIMENSION(:), POINTER :: L0_OMP_MAPPING
! Mpi to omp - mumps agile
        INTEGER(4), DIMENSION(:), POINTER :: MTKO_PROCS_MAP
! for RR on root
        DOUBLE PRECISION, DIMENSION(:), POINTER :: SINGULAR_VALUES
        INTEGER(4) ::  NB_SINGULAR_VALUES
        INTEGER(4) ::  Deficiency, pad16
! To know if OOC files are associated to a saved and so if they should be removed.
        LOGICAL(4) :: ASSOCIATED_OOC_FILES
      END TYPE DMUMPS_STRUC
