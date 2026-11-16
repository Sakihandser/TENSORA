// TENSORA fluid–structure interaction, one-way path: structural response of
// the solid zone to the wall pressure and shear computed by SU2.
//
// The driver only wires files to MFEM 4.10 library calls built from the
// unmodified upstream source:
//   * H1 finite element spaces and GridFunctions carry the SU2 vertex values;
//   * VectorBoundaryFluxLFIntegrator integrates the pressure load  -p n,
//     VectorBoundaryLFIntegrator integrates the wall shear traction tau;
//   * ElasticityIntegrator, FormLinearSystem, CGSolver + GSSmoother solve the
//     linear elastic equilibrium; ComputeElementFlux recovers the stresses.
//
// Usage: mfem_fsi <job-directory>
//   input : fsi.mesh (MFEM v1.0, TRI3/TET4; element attribute = material slot;
//                     boundary attribute 1 wetted interface, 2 clamped,
//                     3/4/5 roller fixing x/y/z)
//           fsi.dat  (slots; lambda mu per slot; tol maxit; vertex count;
//                     per vertex: flag pressure tau_x tau_y [tau_z])
//   output: fsi.out  (status line, applied force, displacement per vertex,
//                     stress per element)

#include "mfem.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>

using namespace mfem;

int main(int argc, char *argv[])
{
   if (argc < 2) { std::cerr << "usage: mfem_fsi <job-dir>\n"; return 2; }
   const std::string dir = argv[1];
   try
   {
      Mesh mesh((dir + "/fsi.mesh").c_str(), 1, 1, false);
      const int dim = mesh.Dimension();
      if (dim != 2 && dim != 3) { std::cerr << "mesh must be 2D or 3D\n"; return 3; }

      std::ifstream in(dir + "/fsi.dat");
      if (!in) { std::cerr << "missing fsi.dat\n"; return 4; }
      int slots = 0;
      in >> slots;
      Vector lambda(slots), mu(slots);
      for (int i = 0; i < slots; i++) { in >> lambda(i) >> mu(i); }
      double tolerance = 1e-12; int max_iter = 100000;
      in >> tolerance >> max_iter;
      int nv = 0;
      in >> nv;
      if (nv != mesh.GetNV()) { std::cerr << "vertex count mismatch\n"; return 5; }

      // Order-1 H1 spaces: one dof per mesh vertex, so SU2 vertex values map
      // directly onto MFEM GridFunctions.
      H1_FECollection fec(1, dim);
      FiniteElementSpace scalar_space(&mesh, &fec);
      FiniteElementSpace vector_space(&mesh, &fec, dim, Ordering::byVDIM);
      GridFunction pressure(&scalar_space), shear(&vector_space);
      for (int v = 0; v < nv; v++)
      {
         int flag = 0; double p = 0.0;
         in >> flag >> p;
         pressure(v) = p;
         for (int d = 0; d < dim; d++) { double t = 0.0; in >> t; shear(v * dim + d) = t; }
      }
      if (!in) { std::cerr << "truncated fsi.dat\n"; return 5; }

      const int nattr = mesh.bdr_attributes.Size() ? mesh.bdr_attributes.Max() : 0;
      Array<int> wetted(std::max(nattr, 5)); wetted = 0; wetted[0] = 1;

      GridFunctionCoefficient pressure_coef(&pressure);
      ProductCoefficient load_coef(-1.0, pressure_coef);       // traction -p n
      VectorGridFunctionCoefficient shear_coef(&shear);

      LinearForm b(&vector_space);
      b.AddBoundaryIntegrator(new VectorBoundaryFluxLFIntegrator(load_coef), wetted);
      b.AddBoundaryIntegrator(new VectorBoundaryLFIntegrator(shear_coef), wetted);
      b.Assemble();

      PWConstCoefficient lambda_func(lambda), mu_func(mu);
      BilinearForm a(&vector_space);
      a.AddDomainIntegrator(new ElasticityIntegrator(lambda_func, mu_func));
      a.Assemble();

      Array<int> ess_tdof_list, part;
      Array<int> clamped(std::max(nattr, 5)); clamped = 0; clamped[1] = 1;
      vector_space.GetEssentialTrueDofs(clamped, ess_tdof_list);
      for (int c = 0; c < dim; c++)
      {
         Array<int> roller(std::max(nattr, 5)); roller = 0; roller[2 + c] = 1;
         vector_space.GetEssentialTrueDofs(roller, part, c);
         ess_tdof_list.Append(part);
      }
      ess_tdof_list.Sort(); ess_tdof_list.Unique();

      GridFunction x(&vector_space);
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

      std::ofstream out(dir + "/fsi.out");
      out << std::setprecision(17);
      out << (cg.GetConverged() ? 1 : 0) << ' ' << cg.GetNumIterations() << ' '
          << cg.GetFinalNorm() << ' ' << cg.GetFinalRelNorm() << ' ' << ess_tdof_list.Size() << '\n';
      // Resultant of the assembled interface load (sum of the load vector).
      const Vector &load = b;
      for (int d = 0; d < dim; d++)
      {
         double sum = 0.0;
         for (int v = 0; v < nv; v++) { sum += load(v * dim + d); }
         out << sum << (d == dim - 1 ? '\n' : ' ');
      }
      for (int v = 0; v < nv; v++)
         for (int d = 0; d < dim; d++) { out << x(v * dim + d) << (d == dim - 1 ? '\n' : ' '); }

      L2_FECollection flux_fec(0, dim);
      ElasticityIntegrator stress_integrator(lambda_func, mu_func);
      Array<int> vdofs;
      Vector u_local, flux;
      const int ncomp = dim == 2 ? 3 : 6;
      for (int e = 0; e < mesh.GetNE(); e++)
      {
         const FiniteElement &el = *vector_space.GetFE(e);
         ElementTransformation &T = *mesh.GetElementTransformation(e);
         vector_space.GetElementVDofs(e, vdofs);
         x.GetSubVector(vdofs, u_local);
         const FiniteElement &flux_el = *flux_fec.FiniteElementForGeometry(mesh.GetElementBaseGeometry(e));
         stress_integrator.ComputeElementFlux(el, T, u_local, flux_el, flux, true);
         // MFEM order: 2D s_xx s_yy s_xy; 3D s_xx s_yy s_zz s_xy s_xz s_yz
         for (int k = 0; k < ncomp; k++) { out << flux(k) << (k == ncomp - 1 ? '\n' : ' '); }
      }
      return cg.GetConverged() ? 0 : 6;
   }
   catch (std::exception &error)
   {
      std::cerr << error.what() << '\n';
      return 7;
   }
}
