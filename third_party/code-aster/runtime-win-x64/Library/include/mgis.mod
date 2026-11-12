!mod$ v1 sum:89393ed643141776
!need$ 554180c599dc39f3 i iso_c_binding
!need$ 72d07276529809c8 i iso_fortran_env
!need$ e284f521c809d929 n mgis_fortran_utilities
module mgis
use,intrinsic::__fortran_builtins,only:__builtin_c_ptr
use,intrinsic::iso_c_binding,only:c_int
use,intrinsic::iso_c_binding,only:c_ptr
use,intrinsic::iso_c_binding,only:c_char
use,intrinsic::iso_c_binding,only:c_null_ptr
use,intrinsic::iso_fortran_env,only:int64
use mgis_fortran_utilities,only:strlen_wrapper
use mgis_fortran_utilities,only:convert_to_c_index
use mgis_fortran_utilities,only:get_empty_string
use mgis_fortran_utilities,only:convert_c_string
use mgis_fortran_utilities,only:convert_fortran_string
private::__builtin_c_ptr
integer(4),parameter::mgis_success=0_4
integer(4),parameter::mgis_failure=1_4
type,bind(c)::mgis_status
integer(4)::exit_status
type(c_ptr)::msg=__builtin_c_ptr(__address=0_8)
end type
type::threadpool
type(c_ptr)::ptr
end type
interface
function report_success() bind(c,name="mgis_report_success") result(r)
import::mgis_status
type(mgis_status)::r
end
end interface
contains
function report_failure(msg) result(r)
character(*,1),intent(in)::msg
type(mgis_status)::r
end
function get_error_message(s) result(msg)
type(mgis_status)::s
character(:,1),allocatable::msg
end
function create_thread_pool(p,n) result(s)
type(threadpool),intent(out)::p
integer(4),intent(in)::n
type(mgis_status)::s
end
function free_thread_pool(p) result(r)
type(threadpool),intent(inout)::p
type(mgis_status)::r
end
end
