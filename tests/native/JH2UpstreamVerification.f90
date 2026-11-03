! Independent host: calls upstream SIGEPS79 directly, without bridge.f90 or C++.
program jh2_upstream_verification
  use iso_c_binding
  implicit none
  real(c_double) :: p(20), old(6), de(6), stress(6), rho0(1), rho(1), epsd(1), mu(1)
  real(c_double) :: sigy(1), dpla(1), defp(1), dmg(1), sound(1), uvar(1,2)
  real(c_double) :: off(1), et(1), varnl(1), planl(1), time, timestep, state(5)
  integer :: ngl(1), ios
  do
    read(*,*,iostat=ios) p,old,de,mu,epsd,rho0,state
    if(ios/=0)exit
    rho=rho0*(1+mu)
    dmg=state(1)
    defp=state(2)
    uvar(1,:)=state(3:4)
    et=state(5)
    off=1
    varnl=0
    planl=0
    ngl=1
    time=0
    timestep=1
    call sigeps79(1,20,2,time,timestep,p,rho0,rho,ngl,sigy,dpla,defp, &
      de(1),de(2),de(3),de(4),de(5),de(6), &
      old(1),old(2),old(3),old(4),old(5),old(6), &
      stress(1),stress(2),stress(3),stress(4),stress(5),stress(6), &
      epsd,dmg,sound,uvar,off,mu,et,0,varnl,1,planl)
    write(*,'(14(es25.16e3,1x))') stress,dmg,defp,uvar,et,sigy,dpla,sound
  end do
end program
