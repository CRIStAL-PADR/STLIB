# -*- coding: utf-8 -*-
import Sofa.Core
from stlib3.visuals import VisualModel


class ElasticMaterialObject(Sofa.Prefab):
    """Creates an object composed of an elastic material."""
    properties = [
        {'name':'volumeMeshFileName',  'type':'string', 'help':'Path to volume mesh file',    'default':''},
        {'name':'name',                'type':'string', 'help':'Node name',                   'default':'ElasticMaterialObject'},
        {'name':'rotation',            'type':'Vec3d',  'help':'Rotation',                    'default':[0.0, 0.0, 0.0]},
        {'name':'translation',         'type':'Vec3d',  'help':'Translation',                 'default':[0.0, 0.0, 0.0]},
        {'name':'scale',               'type':'Vec3d',  'help':'Scale 3d',                    'default':[1.0, 1.0, 1.0]},
        {'name':'surfaceMeshFileName', 'type':'string', 'help':'Path to surface mesh file',   'default':''},
        {'name':'collisionMesh',       'type':'string', 'help':'Path to collision mesh file', 'default':''},
        {'name':'withConstrain',       'type':'bool',   'help':'Add constraint correction',   'default':True},
        {'name':'surfaceColor',        'type':'Vec4d',  'help':'Color of surface mesh',       'default':[1.,1.,1.,1.]},
        {'name':'poissonRatio',        'type':'double', 'help':'Poisson ratio',               'default':0.3},
        {'name':'youngModulus',        'type':'double', 'help':"Young's modulus",             'default':18000},
        {'name':'totalMass',           'type':'double', 'help':'Total mass',                  'default':1.0},
        {'name':'solverName',          'type':'string', 'help':'Solver name',                 'default':''}]

    def __init__(self, *args, **kwargs):
        Sofa.Prefab.__init__(self, *args, **kwargs)

    def init(self):

        # Eulalie: 01/21 the prefab is child of none... so there is no root?
        # root = self.getRoot()
        # if not root.getObject("SofaSparseSolver", warning=False):
        #     if not root.getObject("/Config/SofaSparseSolver", warning=False):
        #         Sofa.msg_info("Missing RequiredPlugin SofaSparseSolver in the scene, add it from Prefab ElasticMaterialObject.")
        #         root.addObject("RequiredPlugin", name="SofaSparseSolver")
        plugins = []

        if self.solverName.value == '':
            plugins.append('SofaImplicitOdeSolver')
            self.integration = self.addObject('EulerImplicitSolver', name='integration')
            plugins.append('SofaSparseSolver')
            self.solver = self.addObject('SparseLDLSolver', name="solver")
            # Eulalie: 01/21 a bit hard to debug... when uncommented, no warning or error shows up, yet all components won't just be created...
            # self.solverName = 'solver'

        if self.volumeMeshFileName.value == '':
            Sofa.msg_error(self, "Unable to create an elastic object because there is no volume mesh provided.")
            return None

        if self.volumeMeshFileName.value.endswith(".msh"):
            self.loader = self.addObject('MeshGmshLoader', name='loader', filename=self.volumeMeshFileName.value, rotation=list(self.rotation.value), translation=list(self.translation.value), scale3d=list(self.scale.value))
        elif self.volumeMeshFileName.value.endswith(".gidmsh"):
            self.loader = self.addObject('GIDMeshLoader', name='loader', filename=self.volumeMeshFileName.value, rotation=list(self.rotation.value), translation=list(self.translation.value), scale3d=list(self.scale.value))
        else:
            self.loader = self.addObject('MeshVTKLoader', name='loader', filename=self.volumeMeshFileName.value, rotation=list(self.rotation.value), translation=list(self.translation.value), scale3d=list(self.scale.value))

        self.container = self.addObject('TetrahedronSetTopologyContainer', src=self.loader.getLinkPath(), name='container')
        self.dofs = self.addObject('MechanicalObject', template='Vec3', name='dofs')

        # To be properly simulated and to interact with gravity or inertia forces, an elasticobject
        # also needs a mass. You can add a given mass with a uniform distribution for an elasticobject
        # by adding a UniformMass component to the elasticobject node
        self.mass = self.addObject('UniformMass', totalMass=self.totalMass.value, name='mass')

        # The next component to add is a FEM forcefield which defines how the elasticobject reacts
        # to a loading (i.e. which deformations are created from forces applied onto it).
        # Here, because the elasticobject is made of silicone, its mechanical behavior is assumed elastic.
        # This behavior is available via the TetrahedronFEMForceField component.
        plugins.append('SofaSimpleFem')
        self.forcefield = self.addObject('TetrahedronFEMForceField', template='Vec3',
                                                 method='large', name='forcefield',
                                                 poissonRatio=self.poissonRatio.value,  youngModulus=self.youngModulus.value)

        if self.withConstrain:
            plugins.append('SofaConstraint')
            self.correction = self.addObject('LinearSolverConstraintCorrection')

        if self.collisionMesh:
            self.addCollisionModel(self.collisionMesh.value, list(self.rotation.value), list(self.translation.value), list(self.scale.value))

        if self.surfaceMeshFileName:
            self.addVisualModel(self.surfaceMeshFileName.value, self.surfaceColor.value, list(self.rotation.value), list(self.translation.value), list(self.scale.value))

        self.addObject('RequiredPlugin', pluginName=plugins)


    def addCollisionModel(self, collisionMesh, rotation=[0.0, 0.0, 0.0], translation=[0.0, 0.0, 0.0], scale=[1., 1., 1.]):
        self.collisionmodel = self.addChild('CollisionModel')
        self.collisionmodel.addObject('MeshSTLLoader', name='loader', filename=collisionMesh, rotation=rotation, translation=translation, scale3d=scale)
        self.collisionmodel.addObject('TriangleSetTopologyContainer', src='@loader', name='container')
        self.collisionmodel.addObject('MechanicalObject', template='Vec3', name='dofs')
        self.collisionmodel.addObject('TriangleCollisionModel')
        self.collisionmodel.addObject('LineCollisionModel')
        self.collisionmodel.addObject('PointCollisionModel')
        self.collisionmodel.addObject('BarycentricMapping')

    def addVisualModel(self, filename, color, rotation, translation, scale=[1., 1., 1.]):
        visualmodel = VisualModel(visualMeshPath=filename, color=color, rotation=rotation, translation=translation, scale=scale)
        self.addChild(visualmodel)

        # Add a BarycentricMapping to deform the rendering model to follow the ones of the
        # mechanical model.
        visualmodel.addObject('BarycentricMapping', name='mapping')


def createScene(rootNode):
    from stlib3.scene import MainHeader

    MainHeader(rootNode, gravity=[0, 0, 0])
    rootNode.addChild(ElasticMaterialObject(name='ElasticMaterialObject1', volumeMeshFileName="mesh/liver.msh", translation=[3.0, 0.0, 0.0]))
    rootNode.addChild(ElasticMaterialObject(name='ElasticMaterialObject2', volumeMeshFileName="mesh/liver.msh", translation=[-3, 0, 0], surfaceMeshFileName="mesh/liver.obj", surfaceColor=[1.0, 0.0, 0.0]))
