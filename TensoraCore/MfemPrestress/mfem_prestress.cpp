// TENSORA 3D blast: initial (geostatic / confining) equilibrium through MFEM.
//
// This driver only wires files to MFEM library calls. The finite element
// space, the elasticity bilinear form (mfem::ElasticityIntegrator), the
// constrained linear system (FormLinearSystem), the PCG solver with Gauss-
// Seidel smoothing and the element stress recovery (ComputeElementFlux) are
// all MFEM 4.10 components built from the unmodified upstream source.
//
// Usage: mfem_prestress <job-directory>
//   input : prestress.mesh  (MFEM v1.0 mesh, TET4, attribute = material slot)
//           prestress.dat   (text: slots, lambda/mu per slot, fixed dofs, nodal forces)
//   output: prestress.out   (text: status line, then 6 stresses per element)
//           displacement.gf (MFEM GridFunction, byVDIM)

#include "mfem.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

using namespace mfem;

int main(int argc, char *argv[])
{
   if (argc < 2) { std::cerr << "usage: mfem_prestress <job-dir>\n"; return 2; }
   const std::string dir = argv[1];
   try
   {
      Mesh mesh((dir + "/prestress.mesh").c_str(), 1, 1, false);
      const int dim = mesh.Dimension();
      if (dim != 3) { std::cerr << "mesh must be 3D\n"; return 3; }

      std::ifstream in(dir + "/prestress.dat");
      if (!in) { std::cerr << "missing prestress.dat\n"; return 4; }
      int slots = 0;
      in >> slots;
      Vector lambda(slots), mu(slots);
      for (int i = 0; i < slots; i++) { in >> lambda(i) >> mu(i); }
      int fixed_count = 0;
      in >> fixed_count;
      Array<int> ess_tdof_list(fixed_count);
      for (int i = 0; i < fixed_count; i++) { in >> ess_tdof_list[i]; }
      double tolerance = 1e-10; int max_iter = 20000;
      in >> tolerance >> max_iter;

      H1_FECollection fec(1, dim);
      FiniteElementSpace fespace(&mesh, &fec, dim, Ordering::byVDIM);
      const int size = fespace.GetTrueVSize();
      Vector force(size);
      for (int i = 0; i < size; i++) { in >> force(i); }
      if (!in) { std::cerr << "truncated prestress.dat\n"; return 5; }

      PWConstCoefficient lambda_func(lambda), mu_func(mu);
      BilinearForm a(&fespace);
      a.AddDomainIntegrator(new ElasticityIntegrator(lambda_func, mu_func));
      a.Assemble();

      // Consistent nodal loads were integrated by TENSORA's existing load
      // assembly; they enter the MFEM linear form as the right-hand side.
      LinearForm b(&fespace);
      static_cast<Vector &>(b) = force;

      GridFunction x(&fespace);
      x = 0.0;
      SparseMatrix A;
      Vector B, X;
      a.FormLinearSystem(ess_tdof_list, x, b, A, X, B);

      GSSmoother M(A);
      CGSolver cg;
      cg.SetRelTol(tolerance);
      cg.SetAbsTol(0.0);
      cg.SetMaxIter(max_iter);
      cg.SetPrintLevel(0);
      cg.SetPreconditioner(M);
      cg.SetOperator(A);
      cg.Mult(B, X);
      a.RecoverFEMSolution(X, b, x);

      {
         std::ofstream gf(dir + "/displacement.gf");
         gf.precision(17);
         x.Save(gf);
      }

      L2_FECollection flux_fec(0, dim);
      ElasticityIntegrator stress_integrator(lambda_func, mu_func);
      std::ofstream out(dir + "/prestress.out");
      out << std::setprecision(17);
      out << (cg.GetConverged() ? 1 : 0) << ' ' << cg.GetNumIterations() << ' '
          << cg.GetFinalNorm() << ' ' << cg.GetFinalRelNorm() << '\n';
      Array<int> vdofs;
      Vector u_local, flux;
      for (int e = 0; e < mesh.GetNE(); e++)
      {
         const FiniteElement &el = *fespace.GetFE(e);
         ElementTransformation &T = *mesh.GetElementTransformation(e);
         fespace.GetElementVDofs(e, vdofs);
         x.GetSubVector(vdofs, u_local);
         const FiniteElement &flux_el = *flux_fec.FiniteElementForGeometry(mesh.GetElementBaseGeometry(e));
         stress_integrator.ComputeElementFlux(el, T, u_local, flux_el, flux, true);
         // MFEM order: s_xx, s_yy, s_zz, s_xy, s_xz, s_yz
         for (int k = 0; k < 6; k++) { out << flux(k) << (k == 5 ? '\n' : ' '); }
      }
      return cg.GetConverged() ? 0 : 6;
   }
   catch (std::exception &error)
   {
      std::cerr << error.what() << '\n';
      return 7;
   }
}
