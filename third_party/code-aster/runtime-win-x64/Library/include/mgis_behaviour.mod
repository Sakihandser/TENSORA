!mod$ v1 sum:52016c4287ba5337
!need$ 554180c599dc39f3 i iso_c_binding
module mgis_behaviour
use,intrinsic::__fortran_builtins,only:__builtin_c_ptr
use,intrinsic::iso_c_binding,only:c_ptr
use,intrinsic::iso_c_binding,only:c_null_ptr
private::__builtin_c_ptr
integer(4),parameter::scalar=0_4
integer(4),parameter::vector=2_4
integer(4),parameter::vector_1d=10_4
integer(4),parameter::vector_2d=18_4
integer(4),parameter::vector_3d=26_4
integer(4),parameter::stensor=1_4
integer(4),parameter::stensor_1d=9_4
integer(4),parameter::stensor_2d=17_4
integer(4),parameter::stensor_3d=25_4
integer(4),parameter::tensor=3_4
integer(4),parameter::tensor_1d=11_4
integer(4),parameter::tensor_2d=19_4
integer(4),parameter::tensor_3d=27_4
integer(4),parameter::higher_order_tensor=4_4
integer(4),parameter::array=5_4
integer(4),parameter::isotropic=0_4
integer(4),parameter::orthotropic=1_4
integer(4),parameter::generalbehaviour=0_4
integer(4),parameter::standardstrainbasedbehaviour=1_4
integer(4),parameter::standardfinitestrainbehaviour=2_4
integer(4),parameter::cohesivezonemodel=3_4
integer(4),parameter::undefinedkinematic=0_4
integer(4),parameter::smallstrainkinematic=1_4
integer(4),parameter::cohesivezonekinematic=2_4
integer(4),parameter::finitestrainkinematic_f_cauchy=3_4
integer(4),parameter::finitestrainkinematic_eto_pk1=4_4
integer(4),parameter::local_storage=0_4
integer(4),parameter::external_storage=1_4
integer(4),parameter::prediction_tangent_operator=-3_4
integer(4),parameter::prediction_secant_operator=-2_4
integer(4),parameter::prediction_elastic_operator=-1_4
integer(4),parameter::integration_no_tangent_operator=0_4
integer(4),parameter::integration_elastic_operator=1_4
integer(4),parameter::integration_secant_operator=2_4
integer(4),parameter::integration_tangent_operator=3_4
integer(4),parameter::integration_consistent_tangent_operator=4_4
integer(4),parameter::integration_without_speed_of_sound=0_4
integer(4),parameter::integration_with_speed_of_sound=1_4
integer(4),parameter::cauchy=0_4
integer(4),parameter::pk2=1_4
integer(4),parameter::pk1=2_4
integer(4),parameter::dsig_df=0_4
integer(4),parameter::ds_degl=1_4
integer(4),parameter::dpk1_df=2_4
integer(4),parameter::dtau_ddf=3_4
type::finitestrainbehaviouroptions
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::behaviour
type(c_ptr)::ptr=__builtin_c_ptr(__address=0_8)
end type
type::behaviourdata
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::state
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::materialstatemanagerinitializer
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::materialstatemanager
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::behaviourintegrationoptions
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::materialdatamanagerinitializer
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
type::materialdatamanager
type(c_ptr),private::ptr=__builtin_c_ptr(__address=0_8)
end type
contains
function get_space_dimension(vs,h) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::vs
character(*,1),intent(in)::h
type(mgis_status)::s
end
function get_stensor_size(vs,h) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::vs
character(*,1),intent(in)::h
type(mgis_status)::s
end
function get_tensor_size(vs,h) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::vs
character(*,1),intent(in)::h
type(mgis_status)::s
end
function get_variable_size(vs,h,t) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::vs
character(*,1),intent(in)::h
integer(4),intent(in)::t
type(mgis_status)::s
end
function create_finite_strain_behaviour_options(o) result(s)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(out)::o
type(mgis_status)::s
end
function finite_strain_behaviour_options_set_stress_measure(o,ss) result(s)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(in)::o
integer(4),intent(in)::ss
type(mgis_status)::s
end
function finite_strain_behaviour_options_set_stress_measure_by_string(o,ss) result(s)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(in)::o
character(*,1),intent(in)::ss
type(mgis_status)::s
end
function finite_strain_behaviour_options_set_tangent_operator(o,to) result(s)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(in)::o
integer(4),intent(in)::to
type(mgis_status)::s
end
function finite_strain_behaviour_options_set_tangent_operator_by_string(o,to) result(s)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(in)::o
character(*,1),intent(in)::to
type(mgis_status)::s
end
function free_finite_strain_behaviour_options(ptr) result(r)
use mgis,only:mgis_status
type(finitestrainbehaviouroptions),intent(inout)::ptr
type(mgis_status)::r
end
function is_standard_finite_strain_behaviour(b,l,bn) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::b
character(*,1),intent(in)::l
character(*,1),intent(in)::bn
type(mgis_status)::s
end
function load_behaviour(b,l,bn,h) result(s)
use mgis,only:mgis_status
type(behaviour),intent(out)::b
character(*,1),intent(in)::l
character(*,1),intent(in)::bn
character(*,1),intent(in)::h
type(mgis_status)::s
end
function load_finite_strain_behaviour(b,o,l,bn,h) result(s)
use mgis,only:mgis_status
type(behaviour),intent(out)::b
type(finitestrainbehaviouroptions),intent(in)::o
character(*,1),intent(in)::l
character(*,1),intent(in)::bn
character(*,1),intent(in)::h
type(mgis_status)::s
end
function rotate_gradients_in_place(g,b,r) result(res)
use mgis,only:mgis_status
real(8),intent(out),target::g(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::res
end
function rotate_gradients_out_of_place(mg,b,gg,r) result(res)
use mgis,only:mgis_status
real(8),intent(out)::mg(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gg(:)
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::res
end
function rotate_array_of_gradients_in_place(g,b,r,s) result(res)
use mgis,only:mgis_status
real(8),intent(out)::g(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::res
end
function rotate_array_of_gradients_out_of_place(mg,b,gg,r,s) result(res)
use mgis,only:mgis_status
real(8),intent(out)::mg(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gg(:)
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::res
end
function rotate_thermodynamic_forces_in_place(tf,b,r) result(res)
use mgis,only:mgis_status
real(8),intent(out)::tf(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::res
end
function rotate_thermodynamic_forces_out_of_place(mtf,b,gtf,r) result(s)
use mgis,only:mgis_status
real(8),intent(out)::mtf(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gtf(:)
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::s
end
function rotate_array_of_thermodynamic_forces_in_place(tf,b,r,s) result(ret)
use mgis,only:mgis_status
real(8),intent(out)::tf(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::ret
end
function rotate_array_of_thermodynamic_forces_out_of_place(mtf,b,gtf,r,s) result(ret)
use mgis,only:mgis_status
real(8),intent(out)::mtf(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gtf(:)
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::ret
end
function rotate_tangent_operator_blocks_in_place(to,b,r) result(s)
use mgis,only:mgis_status
real(8),intent(out)::to(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::s
end
function rotate_tangent_operator_blocks_out_of_place(mto,b,gto,r) result(s)
use mgis,only:mgis_status
real(8),intent(out)::mto(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gto(:)
real(8),intent(in)::r(1_8:9_8)
type(mgis_status)::s
end
function rotate_array_of_tangent_operator_blocks_in_place(to,b,r,s) result(ret)
use mgis,only:mgis_status
real(8),intent(out)::to(:)
type(behaviour),intent(in)::b
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::ret
end
function rotate_array_of_tangent_operator_blocks_out_of_place(mto,b,gto,r,s) result(ret)
use mgis,only:mgis_status
real(8),intent(out)::mto(:)
type(behaviour),intent(in)::b
real(8),intent(in)::gto(:)
real(8),intent(in)::r(1_8:9_8)
integer(8)::s
type(mgis_status)::ret
end
function behaviour_get_tangent_operator_array_size(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_library(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_behaviour_name(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_function_name(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_source(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_author(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_date(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_validator(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_build_id(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_hypothesis(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_tfel_version(l,b) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_gradients_size(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_thermodynamic_forces_size(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_number_of_parameters(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_parameter_name(l,b,n) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_parameter_default_value(v,b,n) result(r)
use mgis,only:mgis_status
real(8),intent(out)::v
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::r
end
function behaviour_get_number_of_material_properties(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_material_property_name(l,b,n) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_material_property_type(t,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::t
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_internal_state_variables_size(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_number_of_internal_state_variables(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_internal_state_variable_name(l,b,n) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_internal_state_variable_type(t,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::t
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_internal_state_variable_type_by_name(t,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::t
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_internal_state_variable_offset(o,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::o
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_internal_state_variable_offset_by_name(o,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::o
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_number_of_external_state_variables(n,b) result(s)
use mgis,only:mgis_status
integer(4)::n
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_get_external_state_variable_name(l,b,n) result(s)
use mgis,only:mgis_status
character(:,1),allocatable,intent(out)::l
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_external_state_variable_type(t,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::t
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_external_state_variable_type_by_name(t,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::t
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_external_state_variable_offset(o,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::o
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_external_state_variable_offset_by_name(o,b,n) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::o
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_computes_stored_energy(v,b) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::v
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_computes_dissipated_energy(v,b) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::v
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_has_bounds(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_has_lower_bound(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_lower_bound(v,b,n) result(s)
use mgis,only:mgis_status
real(8),intent(out)::v
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_has_upper_bound(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_upper_bound(v,b,n) result(s)
use mgis,only:mgis_status
real(8),intent(out)::v
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_has_physical_bounds(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_has_lower_physical_bound(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_lower_physical_bound(v,b,n) result(s)
use mgis,only:mgis_status
real(8),intent(out)::v
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_has_upper_physical_bound(r,b,n) result(s)
use mgis,only:mgis_status
logical(4),intent(out)::r
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function behaviour_get_upper_physical_bound(v,b,n) result(s)
use mgis,only:mgis_status
real(8),intent(out)::v
type(behaviour),intent(in)::b
character(*,1),intent(in)::n
type(mgis_status)::s
end
function free_behaviour(ptr) result(r)
use mgis,only:mgis_status
type(behaviour),intent(inout)::ptr
type(mgis_status)::r
end
function allocate_behaviour_data(d,b) result(s)
use mgis,only:mgis_status
type(behaviourdata),intent(out)::d
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function behaviour_data_get_behaviour(b,d) result(s)
use mgis,only:mgis_status
type(behaviour),intent(out)::b
type(behaviourdata),intent(in)::d
type(mgis_status)::s
end
function behaviour_data_get_state_0(s0,d) result(s)
use mgis,only:mgis_status
type(state),intent(out)::s0
type(behaviourdata),intent(in)::d
type(mgis_status)::s
end
function behaviour_data_get_state_1(s1,d) result(s)
use mgis,only:mgis_status
type(state),intent(out)::s1
type(behaviourdata),intent(in)::d
type(mgis_status)::s
end
function behaviour_data_set_time_increment(d,dt) result(s)
use mgis,only:mgis_status
type(behaviourdata),intent(in)::d
real(8)::dt
type(mgis_status)::s
end
function behaviour_data_get_time_step_scaling_factor(rdt,d) result(s)
use mgis,only:mgis_status
real(8)::rdt
type(behaviourdata),intent(in)::d
type(mgis_status)::s
end
function behaviour_data_get_tangent_operator(k,d) result(s)
use mgis,only:mgis_status
real(8),intent(out),pointer::k(:,:)
type(behaviourdata),intent(in)::d
type(mgis_status)::s
end
function update_behaviour_data(d) result(r)
use mgis,only:mgis_status
type(behaviourdata),intent(in)::d
type(mgis_status)::r
end
function revert_behaviour_data(d) result(r)
use mgis,only:mgis_status
type(behaviourdata),intent(in)::d
type(mgis_status)::r
end
function free_behaviour_data(ptr) result(r)
use mgis,only:mgis_status
type(behaviourdata),intent(inout)::ptr
type(mgis_status)::r
end
function state_set_mass_density(s,v) result(r)
use mgis,only:mgis_status
type(state),intent(in)::s
real(8)::v
type(mgis_status)::r
end
function state_set_gradient_by_name(s,n,v) result(r)
use mgis,only:mgis_status
type(state),intent(in)::s
character(*,1),intent(in)::n
real(8),target::v(1_8:*)
type(mgis_status)::r
end
function state_set_material_property_by_name(s,n,v) result(r)
use mgis,only:mgis_status
type(state),intent(in)::s
character(*,1),intent(in)::n
real(8),intent(in)::v
type(mgis_status)::r
end
function state_get_material_property_by_name(v,s,n) result(r)
use mgis,only:mgis_status
real(8),intent(out)::v
type(state),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function state_get_internal_state_variable_by_offset(v,s,o) result(r)
use mgis,only:mgis_status
real(8),intent(out)::v
type(state),intent(in)::s
integer(4),intent(in)::o
type(mgis_status)::r
end
function state_get_internal_state_variables(isvs,s,b) result(r)
use mgis,only:mgis_status
real(8),intent(out),pointer::isvs(:)
type(state),intent(in)::s
type(behaviour),intent(in)::b
type(mgis_status)::r
end
function state_set_scalar_external_state_variable_by_name(s,n,v) result(r)
use mgis,only:mgis_status
type(state),intent(in)::s
character(*,1),intent(in)::n
real(8),intent(in)::v
type(mgis_status)::r
end
function state_get_external_state_variable_by_name(v,s,n) result(r)
use mgis,only:mgis_status
real(8),intent(out)::v
type(state),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function msm_initializer_bind_gradients(st,a,n) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(in)::st
real(8),intent(out),target::a(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function msm_initializer_bind_thermodynamic_forces(st,a,n) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(in)::st
real(8),intent(out),target::a(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function msm_initializer_bind_internal_state_variables(st,a,n) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(in)::st
real(8),intent(out),target::a(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function msm_initializer_bind_stored_energies(st,a,n) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(in)::st
real(8),intent(out),target::a(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function msm_initializer_bind_dissipated_energies(st,a,n) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(in)::st
real(8),intent(out),target::a(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function create_material_data_manager_initializer(d) result(s)
use mgis,only:mgis_status
type(materialdatamanagerinitializer),intent(out)::d
type(mgis_status)::s
end
function material_data_manager_initializer_get_state_0_initializer(s0,d) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(out)::s0
type(materialdatamanagerinitializer),intent(in)::d
type(mgis_status)::s
end
function material_data_manager_initializer_get_state_1_initializer(s1,d) result(s)
use mgis,only:mgis_status
type(materialstatemanagerinitializer),intent(out)::s1
type(materialdatamanagerinitializer),intent(in)::d
type(mgis_status)::s
end
function material_data_manager_initializer_bind_tangent_operator(d,k,n) result(s)
use mgis,only:mgis_status
type(materialdatamanagerinitializer),intent(in)::d
real(8),intent(out),target::k(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function material_data_manager_initializer_bind_speed_of_sound(d,p,n) result(s)
use mgis,only:mgis_status
type(materialdatamanagerinitializer),intent(in)::d
real(8),intent(out),target::p(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::s
end
function free_material_data_manager_initializer(ptr) result(r)
use mgis,only:mgis_status
type(materialdatamanagerinitializer),intent(inout)::ptr
type(mgis_status)::r
end
function create_behaviour_integration_options(o) result(s)
use mgis,only:mgis_status
type(behaviourintegrationoptions),intent(out)::o
type(mgis_status)::s
end
function behaviour_integration_options_set_speed_of_sound_flag(o,ss) result(s)
use mgis,only:mgis_status
type(behaviourintegrationoptions),intent(in)::o
integer(4),intent(in)::ss
type(mgis_status)::s
end
function behaviour_integration_options_set_integration_type(o,ss) result(s)
use mgis,only:mgis_status
type(behaviourintegrationoptions),intent(in)::o
integer(4),intent(in)::ss
type(mgis_status)::s
end
function free_behaviour_integration_options(ptr) result(r)
use mgis,only:mgis_status
type(behaviourintegrationoptions),intent(inout)::ptr
type(mgis_status)::r
end
function create_material_data_manager(d,b,n) result(s)
use mgis,only:mgis_status
type(materialdatamanager),intent(out)::d
type(behaviour),intent(in)::b
integer(4),intent(in)::n
type(mgis_status)::s
end
function create_material_data_manager_with_initializer(d,b,i,n) result(s)
use mgis,only:mgis_status
type(materialdatamanager),intent(out)::d
type(behaviour),intent(in)::b
type(materialdatamanagerinitializer),intent(in)::i
integer(4),intent(in)::n
type(mgis_status)::s
end
function material_data_manager_set_thread_safe(d,b) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
integer(8),intent(in)::b
type(mgis_status)::r
end
function material_data_manager_allocate_array_of_tangent_operator_blocks(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function material_data_manager_use_array_of_tangent_operator_blocks(d,p,n) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
real(8),intent(out),target::p(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::r
end
function material_data_manager_release_array_of_tangent_operator_blocks(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function material_data_manager_allocate_array_of_speed_of_sounds(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function material_data_manager_use_array_of_speed_of_sounds(d,p,n) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
real(8),intent(out),target::p(1_8:*)
integer(4),intent(in)::n
type(mgis_status)::r
end
function material_data_manager_release_array_of_speed_of_sounds(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function material_data_manager_get_state_0(s0,d) result(s)
use mgis,only:mgis_status
type(materialstatemanager),intent(out)::s0
type(materialdatamanager),intent(in)::d
type(mgis_status)::s
end
function material_data_manager_get_state_1(s1,d) result(s)
use mgis,only:mgis_status
type(materialstatemanager),intent(out)::s1
type(materialdatamanager),intent(in)::d
type(mgis_status)::s
end
function material_state_manager_get_number_of_integration_points(n,s) result(r)
use mgis,only:mgis_status
integer(4),intent(out)::n
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_gradients_stride(g_stride,s) result(r)
use mgis,only:mgis_status
integer(4),intent(out)::g_stride
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_gradients(g,s) result(r)
use mgis,only:mgis_status
real(8),intent(out),pointer::g(:,:)
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_thermodynamic_forces_stride(tf_stride,s) result(r)
use mgis,only:mgis_status
integer(4),intent(out)::tf_stride
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_thermodynamic_forces(tf,s) result(r)
use mgis,only:mgis_status
real(8),intent(out),pointer::tf(:,:)
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_set_uniform_scalar_material_property(s,n,v) result(r)
use mgis,only:mgis_status
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
real(8),intent(in)::v
type(mgis_status)::r
end
function material_state_manager_is_material_property_defined(b,s,n) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function material_state_manager_is_material_property_uniform(b,s,n) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function material_state_manager_set_uniform_scalar_mass_density(s,v) result(r)
use mgis,only:mgis_status
type(materialstatemanager),intent(in)::s
real(8),intent(in)::v
type(mgis_status)::r
end
function material_state_manager_is_mass_density_defined(b,s) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_is_mass_density_uniform(b,s) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_internal_state_variables_stride(n_isvs,s) result(r)
use mgis,only:mgis_status
integer(4),intent(out)::n_isvs
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_get_internal_state_variables(isvs,s) result(r)
use mgis,only:mgis_status
real(8),intent(out),pointer::isvs(:,:)
type(materialstatemanager),intent(in)::s
type(mgis_status)::r
end
function material_state_manager_set_us_external_state_variable(s,n,v) result(r)
use mgis,only:mgis_status
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
real(8),intent(in)::v
type(mgis_status)::r
end
function material_state_manager_is_external_state_variable_defined(b,s,n) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function material_state_manager_is_external_state_variable_uniform(b,s,n) result(r)
use mgis,only:mgis_status
logical(4),intent(out)::b
type(materialstatemanager),intent(in)::s
character(*,1),intent(in)::n
type(mgis_status)::r
end
function material_data_manager_get_tangent_operator(k,m) result(r)
use mgis,only:mgis_status
real(8),intent(out),pointer::k(:,:,:)
type(materialdatamanager),intent(in)::m
type(mgis_status)::r
end
function free_material_data_manager(ptr) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(inout)::ptr
type(mgis_status)::r
end
function update_material_data_manager(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function revert_material_data_manager(d) result(r)
use mgis,only:mgis_status
type(materialdatamanager),intent(in)::d
type(mgis_status)::r
end
function integrate(r,d,b) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::r
type(behaviourdata),intent(in)::d
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function integrate_debug(r,d,b) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::r
type(behaviourdata),intent(in)::d
type(behaviour),intent(in)::b
type(mgis_status)::s
end
function integrate_material_data_manager(r,p,m,i,dt) result(s)
use mgis,only:mgis_status
use mgis,only:threadpool
integer(4),intent(out)::r
type(threadpool),intent(in)::p
type(materialdatamanager),intent(in)::m
integer(4),intent(in)::i
real(8),intent(in)::dt
type(mgis_status)::s
end
function integrate_debug_material_data_manager(r,p,m,i,dt) result(s)
use mgis,only:mgis_status
use mgis,only:threadpool
integer(4),intent(out)::r
type(threadpool),intent(in)::p
type(materialdatamanager),intent(in)::m
integer(4),intent(in)::i
real(8),intent(in)::dt
type(mgis_status)::s
end
function integrate_material_data_manager_with_options(r,p,m,i,dt) result(s)
use mgis,only:mgis_status
use mgis,only:threadpool
integer(4),intent(out)::r
type(threadpool),intent(in)::p
type(materialdatamanager),intent(in)::m
type(behaviourintegrationoptions),intent(in)::i
real(8),intent(in)::dt
type(mgis_status)::s
end
function integrate_debug_material_data_manager_with_options(r,p,m,i,dt) result(s)
use mgis,only:mgis_status
use mgis,only:threadpool
integer(4),intent(out)::r
type(threadpool),intent(in)::p
type(materialdatamanager),intent(in)::m
type(behaviourintegrationoptions),intent(in)::i
real(8),intent(in)::dt
type(mgis_status)::s
end
function integrate_material_data_manager_part(r,m,i,dt,ni,ne) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::r
type(materialdatamanager),intent(in)::m
integer(4),intent(in),value::i
real(8),intent(in)::dt
integer(4)::ni
integer(4)::ne
type(mgis_status)::s
end
function integrate_debug_material_data_manager_part(r,m,i,dt,ni,ne) result(s)
use mgis,only:mgis_status
integer(4),intent(out)::r
type(materialdatamanager),intent(in)::m
integer(4),intent(in),value::i
real(8),intent(in)::dt
integer(4)::ni
integer(4)::ne
type(mgis_status)::s
end
end
