! C ABI only: all constitutive calculations are performed by upstream SIGEPS79.
! Distributed under AGPL-3.0-or-later, like the linked OpenRadioss component.
subroutine tensora_jh2_step(parameters, stress_old, strain_increment, mu, rate, &
                          density, state, stress_new, results) bind(C)
  use iso_c_binding
  implicit none
  real(c_double), intent(in) :: parameters(20), stress_old(6), strain_increment(6)
  real(c_double), value :: mu, rate, density
  ! state: damage, equivalent plastic strain, bulking pressure, previous yield, ET
  real(c_double), intent(inout) :: state(5)
  real(c_double), intent(out) :: stress_new(6), results(3)
  real(c_double) :: rho0(1), rho(1), sigy(1), dpla(1), defp(1), dmg(1)
  real(c_double) :: sound(1), uvar(1,2), off(1), et(1), varnl(1), planl(1)
  real(c_double) :: epsd(1), amu(1), time, timestep
  integer :: ngl(1)
  rho0 = density
  rho = density*(1.0_c_double+mu)
  epsd = rate
  amu = mu
  dmg = state(1)
  defp = state(2)
  uvar(1,:) = state(3:4)
  et = state(5)
  off = 1.0_c_double
  varnl = 0.0_c_double
  planl = 0.0_c_double
  time = 0.0_c_double
  timestep = 1.0_c_double
  ngl = 1
  call sigeps79(1,20,2,time,timestep,parameters,rho0,rho,ngl,sigy,dpla,defp, &
    strain_increment(1),strain_increment(2),strain_increment(3), &
    strain_increment(4),strain_increment(5),strain_increment(6), &
    stress_old(1),stress_old(2),stress_old(3),stress_old(4),stress_old(5),stress_old(6), &
    stress_new(1),stress_new(2),stress_new(3),stress_new(4),stress_new(5),stress_new(6), &
    epsd,dmg,sound,uvar,off,amu,et,0,varnl,1,planl)
  state(1) = dmg(1)
  state(2) = defp(1)
  state(3:4) = uvar(1,:)
  state(5) = et(1)
  results = [sigy(1),dpla(1),sound(1)]
end subroutine

integer(c_int) function tensora_jh2_abi() bind(C)
  use iso_c_binding
  implicit none
  tensora_jh2_abi = 1
end function

function tensora_jh2_source() result(pointer) bind(C)
  use iso_c_binding
  implicit none
  type(c_ptr) :: pointer
  character(kind=c_char,len=41), target, save :: commit = &
    'bad6688602d770e019b75773d2d5a48b4f9bd918'//c_null_char
  pointer = c_loc(commit)
end function
