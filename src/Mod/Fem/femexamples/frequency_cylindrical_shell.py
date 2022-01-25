# ***************************************************************************
# *   Copyright (c) 2022 Bernd Hahnebach <bernd@bimstatik.org>              *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD

import Draft

import ObjectsFem

from femmesh.gmshtools import GmshTools

from . import manager
from .manager import init_doc


def get_information():
    return {
        "name": "Frequency Analysis Cylindrical Shell",
        "meshtype": "face",
        "meshelement": "Quad4",
        "constraints": ["fixed"],
        "solvers": ["calculix", "ccxtools"],
        "material": "solid",
        "equation": "frequency",
    }


def get_explanation(header=""):
    return (
        header
        + """

To run the example from Python console use:
from femexamples.frequency_cylindrical_shell import setup
setup()


See forum topic post:
https://forum.freecadweb.org/viewtopic.php?f=18&t=65382#p564156
frequency analysis for cylindrical shell

"""
    )


def setup(doc=None, solvertype="ccxtools"):

    # init FreeCAD document
    if doc is None:
        doc = init_doc()

    # explanation object
    # just keep the following line and change text string in get_explanation method
    manager.add_explanation_obj(
        doc, get_explanation(manager.get_header(get_information()))
    )

    # geometric object
    # create cylinder
    cyl_obj = doc.addObject("Part::Cylinder", "Cylinder")
    cyl_obj.Radius = 5000
    cyl_obj.Height = 5000
    doc.recompute()
    if FreeCAD.GuiUp:
        cyl_obj.ViewObject.Document.activeView().viewAxonometric()
        cyl_obj.ViewObject.Document.activeView().fitAll()

    # create cylindrical shell
    Draft.downgrade(cyl_obj, delete=True)
    doc.removeObject("Face001")
    doc.removeObject("Face002")
    doc.recompute()

    # analysis
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")

    # solver
    if solvertype == "calculix":
        solver_obj = ObjectsFem.makeSolverCalculix(doc, "SolverCalculiX")
    elif solvertype == "ccxtools":
        solver_obj = ObjectsFem.makeSolverCalculixCcxTools(doc, "CalculiXccxTools")
        solver_obj.WorkingDir = u""
    else:
        FreeCAD.Console.PrintWarning(
            "Not known or not supported solver type: {}. "
            "No solver object was created.\n".format(solvertype)
        )
    if solvertype == "calculix" or solvertype == "ccxtools":
        solver_obj.SplitInputWriter = False
        solver_obj.AnalysisType = "frequency"
        solver_obj.GeometricalNonlinearity = "linear"
        solver_obj.ThermoMechSteadyState = False
        solver_obj.MatrixSolverType = "default"
        solver_obj.IterationsControlParameterTimeUse = False
        solver_obj.EigenmodesCount = 10
        solver_obj.EigenmodeHighLimit = 1000000.0
        solver_obj.EigenmodeLowLimit = 0.01
    analysis.addObject(solver_obj)

    # material
    material_obj = analysis.addObject(
        ObjectsFem.makeMaterialSolid(doc, "MechanicalMaterial")
    )[0]
    mat = material_obj.Material
    mat["Name"] = "Steel-Generic"
    mat["YoungsModulus"] = "210 GPa"
    mat["PoissonRatio"] = "0.30"
    mat["Density"] = "7900 kg/m^3"
    material_obj.Material = mat
    analysis.addObject(material_obj)

    # constraint displacement xyz
    con_disp_xyz = ObjectsFem.makeConstraintDisplacement(doc, "Fix_Z")
    con_disp_xyz.References = [(doc.Face, "Edge2")]
    con_disp_xyz.xFix = False
    con_disp_xyz.xFree = True
    con_disp_xyz.xDisplacement = 0.0
    con_disp_xyz.yFix = False
    con_disp_xyz.yFree = True
    con_disp_xyz.yDisplacement = 0.0
    con_disp_xyz.zFix = True
    con_disp_xyz.zFree = False
    con_disp_xyz.zDisplacement = 0.0
    analysis.addObject(con_disp_xyz)

    # add thickness
    geo_thickness = ObjectsFem.makeElementGeometry2D(doc, 10)
    analysis.addObject(geo_thickness)

    # mesh
    femmesh_obj = ObjectsFem.makeMeshGmsh(doc, "Cylinder_Shell_Mesh")
    femmesh_obj.Part = doc.Face
    femmesh_obj.ElementDimension = "2D"
    femmesh_obj.ElementOrder = "2nd"
    femmesh_obj.Algorithm2D = "Packing Parallelograms"
    femmesh_obj.RecombinationAlgorithm = "Simple"
    femmesh_obj.HighOrderOptimize = "Optimization"
    femmesh_obj.RecombineAll = True
    femmesh_obj.SecondOrderLinear = True
    femmesh_obj.CharacteristicLengthMax = "300.0 mm"

    gmsh_mesh = GmshTools(femmesh_obj)
    error = gmsh_mesh.create_mesh()
    FreeCAD.Console.PrintMessage(error)

    analysis.addObject(femmesh_obj)
    doc.recompute()
    return doc
