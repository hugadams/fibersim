from basic_material import BasicMaterial
from material_models import Sellmeir, Dispwater
from traits.api import *
from traitsui.api import *	
from interfaces import IMixer, IStorage, IMaterial
import math
from modeltree_v2 import Model
from material_mixer_v2 import MG_Mod, Bruggeman, QCACP, MG

class CompositeMaterial(BasicMaterial):
    '''Still inherits basic traits like earray, narray and how they are interrelated'''

    modeltree = Instance(Model)#,())

    Material1=Instance(IMaterial)
    Material2=Instance(IMaterial)   #Make these classes later

    Mat1History=List(IMaterial)  #When the materials change, this logs them.  Useful for advanced stuff
    Mat2History=List(IMaterial)

    Mix=Instance(IMixer)

    MixingStyle=Enum('MGMOD', 'Bruggeman (root)', 'QCACP (root)', 'MG (root)')
    Vfrac=DelegatesTo('Mix')	#Coordinates with parameter in mixer
    earray=DelegatesTo('Mix', prefix='mixedarray')

    selectmat1=Button 
    selectmat2=Button

    mixgroup=Group(   VGroup(
        HGroup(
            Item('MixingStyle', label='Mixing Method', show_label=False),
            Item('Mix', editor=InstanceEditor(), style='custom', label='Mixing Parameters', show_label=False ),
            ),	
        Item('mviewbutton', label='Show Mixed Material', show_label=False),
        ),    #Group Label here
                      label='Mixing Parameters')            #View Label 

    compmatgroup=Group(Item('mat_name', label='Material Name'),
                       Tabbed( 
                           Item('Material1', editor=InstanceEditor(), style='custom', label='Solute', show_label=False),
                           Item('Material2', editor=InstanceEditor(), style='custom', label='Solvent', show_label=False),
                           ),
                       HGroup(		
                           Item('selectmat1', label='Change Solute', show_label=False), 
                           Item('selectmat2', label='Change Solvent', show_label=False),
                           ),
                       label='Materials')

    traits_view=View(Item('allbutt', label='Show Allview'),
                     Item('specparms', style='custom'),
                     Include('compmatgroup' ),
                     Include('mixgroup'), 
                     #Item('Mat1History', editor=ListEditor(), style='custom'), 
                     resizable=True, buttons=OKCancelButtons)

    def __init__(self, *args, **kwargs):
        super(CompositeMaterial, self).__init__(*args, **kwargs)
        self.sync_trait('specparms', self.Material1, 'specparms', mutual=True)  	 
        self.sync_trait('specparms', self.Material2, 'specparms', mutual=True)  
        self.sync_trait('Material1', self.Mix, 'solutematerial')	
        self.sync_trait('Material2', self.Mix, 'solventmaterial') 
        self.update_allplots()

    def simulation_requested(self):
        out = super(CompositeMaterial, self).simulation_requested()
        
        out.update({
            'material1':self.Material1.simulation_requested(),
            'material2':self.Material2.simulation_requested(), 
            'mixing_style':self.MixingStyle,
            'Vfrac':self.Vfrac})
        return out

#	def update_allplots(self): 
#			self.allplots={'Dielectric '+str(self.Material1.mat_name):self.Material1.eplot,  'Dielectric '+str(self.Material2.mat_name):self.Material2.eplot, 
#			'Refractive Index  '+str(self.Material1.mat_name):self.Material1.nplot, 'Refractive Index  '+str(self.Material2.mat_name):self.Material2.nplot}

    def _Material1_default(self): 
        mat1def=Sellmeir()
        self.Mat1History.append(mat1def)
        return mat1def

    def _Material2_default(self): 	
        mat2def=Dispwater()
        self.Mat2History.append(mat2def)
        return mat2def

    def _Mix_default(self): 
        return MG_Mod()

    
    def _mat_name_default(self): 
        return self.Material1.mat_name + '  IN   ' + self.Material2.mat_name


    def _MixingStyle_changed(self): 
        self.update_mix()
        self.update_mview()

    def _Material1_changed(self): 
        self.sync_trait('specparms', self.Material1, 'specparms', mutual=True)  	  #This is necessary because syncing is only done for the object
        self.sync_trait('Material1', self.Mix, 'solutematerial')
        self.update_allplots()
        self.Mat1History.append(self.Material1)


    def _Material2_changed(self): 
        self.sync_trait('specparms', self.Material2, 'specparms', mutual=True)  	  #This is necessary because syncing is only done for the object
        self.sync_trait('Material2', self.Mix, 'solventmaterial')
        self.update_allplots()
        self.Mat2History.append(self.Material2)


    def _Mix_changed(self):
        '''When I change mix, I make a new object, so this guarantees they are synchd'''
        self.sync_trait('Material1', self.Mix, 'solutematerial')
        self.sync_trait('Material2', self.Mix, 'solventmaterial')


    def update_mix(self):
        if self.MixingStyle=='MG (root)':
            self.Mix=MG(Vfrac=self.Vfrac) #vfrac because don't want it to reset to default

        elif self.MixingStyle=='Bruggeman (root)':
            self.Mix=Bruggeman(Vfrac=self.Vfrac)

        elif self.MixingStyle=='QCACP (root)':
            self.Mix=QCACP(Vfrac=self.Vfrac)

        elif self.MixingStyle=='MGMOD':
            self.Mix=MG_Mod(Vfrac=self.Vfrac)


    def _selectmat1_fired(self): 
        '''Used to select material.  The exceptions are if the user returns nothing or selects a folder rather than an object for example'''
        self.modeltree.configure_traits(kind='modal') #Leave as configure traits not edit traits
        try:
            selected_adapter=self.modeltree.current_selection
            selected_adapter.populate_object()
            self.Material1=selected_adapter.matobject	
        except (TypeError, AttributeError):  #If user selects none, or selects a folder object, not an actual selection
            pass

    def _selectmat2_fired(self): 
        self.modeltree.configure_traits(kind='modal')
        try:
            selected_adapter=self.modeltree.current_selection
            selected_adapter.populate_object()
            self.Material2=selected_adapter.matobject
        except (TypeError, AttributeError):  
            pass



class CompositeMaterial_Equiv(CompositeMaterial):
    """From Effective THeory of composites with interphase:
          
    Computes a complex sphere from a core/shell sphere.  In this case, material 1 refers to the
    core material and material 2 refers to the shell material.  Thus, the interpretation of inclusion/solvent
    is no longer valid!  Medium material never involved in this computation
    """
    from material_mixer_v2 import EquivMethod, CustomEquiv
    r_particle=Float(12)
    shell_width=Float(2)
    MixingStyle=Enum('Equivalence', 'Custom Equiv') 

    traits_view=View=View(#Item('r_particle'), 
                       Item('mviewbutton', show_label=False, label='Show Equivalent Complex Dielectric'),
                       HGroup(
                          Item('MixingStyle'),
                          Item('Material1', label='Core Material'), 
                          Item('Material2', label='Shell Material'),   
                          ),

                          Item('Mix', style='custom'),  
                          HGroup(
                              # These labels are kind of specific to nanoparticles, probably want more general
                              # but how do I set labels from advanced_object_v2.py calling this view?
                              Item('selectmat1', show_label=False, label='Choose Core Material'),
                              Item('selectmat2', show_label=False, label='Choose Shell Material'),
                          )
                          )

    def __init__(self, *args, **kwargs):
        super(CompositeMaterial_Equiv, self).__init__(*args, **kwargs)
        self.sync_trait('r_particle', self.Mix, 'r_particle', mutual=True)  
        self.sync_trait('shell_width', self.Mix, 'shell_width', mutual=True)		

    def update_mix(self):
        if self.MixingStyle=='Equivalence':
            self.Mix=self.EquivMethod()

        elif self.MixingStyle=='Custom Equiv':
            self.Mix=self.CustomEquiv()

        self.sync_trait('r_particle', self.Mix, 'r_particle', mutual=True)  
        self.sync_trait('shell_width', self.Mix, 'shell_width', mutual=True) #Yes neccessary 	  		  	

    def _MixingStyle_default(self): 
        return 'Custom Equiv'

    def _Mix_default(self):
        return self.CustomEquiv()


class SphericalInclusions(CompositeMaterial):
    '''Composite material of inclusions of spheres are integrated with the VFrac parameter in volume'''
    ###SINCE ONLY METHODS I USE SO FAR USE SPHERICAL PARTICLES, THIS HAS unitvolume_sphere WHICH IS FOR SPHERICAL INCLUSIONS ONLY###
    platform_type=Str
    particle_type=Str('Spherical Inclusions')  
    mat_name=Str('Composite Material with Spherical Inclusions')

    r_particle=Float(2.0)     #Radius parameters for r_particle and r_platform respectively
    r_platform=Float(12.0)

    shell_width=Property(Float, depends_on='r_particle')  #Thickness of shell determined by 2r inclusion	

    vbox=Property(Float, depends_on='r_particle')           #Box defined by diameter of sphere
    unitvolume=Property(Float, depends_on='r_particle')     #Total amount of volume occupied by the sphere 
    VT=Property(Float, depends_on='r_particle, r_platform') #DEFINED SEPARATELY FOR DIFFERENT PLATFORM TYPES

    N_tot=Property(Float, depends_on='VT, vbox')
    N_occ=Property(Float, depends_on='Vfrac, VT, unitvolume')

    vinc_occ=Property(Float, depends_on='N_occ, unitvolume')  #Total volume of the inclusions
    vshell_occ=Property(Float, depends_on='N_occ, vbox')      #Total volume of the shell filled by boxes

    coverage=Property(Float, depends_on='N_occ, N_tot')

    def __init__(self, *args, **kwargs):
        super(SphericalInclusions, self).__init__(*args, **kwargs)

    def _get_shell_width(self):
        return 2.0*self.r_particle #Shell thickness is d_particle
    
    def _set_shell_width(self, width):
        """ Updates r_particle to 1/2 shell_width"""
        self.r_particle = 0.5 * width


    def _get_vbox(self): 
        return 8.0*(self.r_particle**3)           #Square boxes of volumes

    def _get_vinc_occ(self): 
        return self.N_occ*self.unitvolume

    def _get_vshell_occ(self): 
        return self.N_occ*self.vbox

    def _get_unitvolume(self): 
        value=(4.0*math.pi/3.0)*self.r_particle**3  #THIS IS ONLY VALID FOR SPHERE
        return round(value, 2)

    def _get_N_tot(self): 
        return int(self.VT/self.vbox)   #Total number of available boxes is Vbox/VT

    def _get_N_occ(self): 
        try:
            return int((self.Vfrac * self.VT)/(self.unitvolume))
        except ZeroDivisionError:
            return 0.0        

    def _set_N_occ(self, Nocc): 
        self.Vfrac= (Nocc * self.unitvolume)/self.VT 

    def _get_coverage(self): 
        try:
            return round ( (float(self.N_occ) / float(self.N_tot) )*100.0 , 4)	
        except ZeroDivisionError:
            return 0.0
   
    def _set_coverage(self, coverage):
        self.N_occ=int( (coverage * self.N_tot) / 100.0	)


    def simulation_requested(self):
        out = super(SphericalInclusions, self).simulation_requested()
        
        # Probably want more, but lazy
        out['coverage'] = self.coverage
        out['platform'] = self.platform_type
        out['r_particle'] = self.r_particle
        out['r_plastform'] = self.r_platform

        return out
        

class SphericalInclusions_Shell(SphericalInclusions):
    '''Used for sphere/shell nanoparticles; shell thickness is automatically determined by r_particle (aka biotin radius)'''

    platform_type=Str('Shell Platform')   #Core particle  (Usually NP)

    inclusionsgroup=Group(
        HGroup(Item('particle_type', style='readonly'), Item('platform_type', style='readonly')), 
        HGroup( 
            Item('r_particle', label='Inclusion radius'), Item('shell_width', style='readonly')),
        (Item('r_platform')),

        HGroup(Item('coverage', label='Shell Coverage %'),Item('vinc_occ', label='Total inclusion volume') ),
        HGroup(Item('N_occ', label='Occupied Sites     '), Item('N_tot', label='Total Sites')),
        HGroup(Item('vshell_occ', label='Shell volume occupied'), Item('VT', label='Total shell volume')),
        Include('mixgroup'),
        label='Shell Inclusions and Mixing'    )

    traits_view=View(
        Include('compmatgroup'), Include('inclusionsgroup')
    )

    def __init__(self, *args, **kwargs):
        super(SphericalInclusions_Shell, self).__init__(*args, **kwargs)


    def _get_VT(self): 
        return round ( 
            ((4.0*math.pi/3.0) * (  (self.r_platform+2.0*self.r_particle)**3 - self.r_platform**3 )) 
                    ,2)


class SphericalInclusions_Disk(SphericalInclusions):

    platform_type=Str('Disk')                 #Fiber endface
    particle_type=Str('Spherical Particles')  #Nanoparticles

    ### For easier use when playing w/ research results
    d_particle=Property(Float, depends_on='r_particle')
    d_platform=Property(Float, depends_on='r_platform')		

    def __init__(self, *args, **kwargs):
        super(SphericalInclusions_Disk, self).__init__(*args, **kwargs)

    def _r_platform_default(self): return 31250.0 #62.5uM diameter

    def _get_d_particle(self): 
        return 2.0*self.r_particle
    
    def _get_d_platform(self): 
        return 2.0*self.r_platform

    def _set_d_particle(self, d): 
        self.r_particle = d/2.0

    def _set_d_platform(self, d): 
        self.r_platform = d/2.0

    def _get_VT(self): 
        return round( math.pi * self.r_platform**2 * self.shell_width, 2)

    inclusionsgroup=Group(
        HGroup(Item('particle_type', style='readonly'), 
               Item('platform_type', style='readonly')), 
        HGroup( 
            Item('d_particle', label='Particle Diameter'),
            Item('d_platform', label='Platform Diameter'),	                                 
            Item('r_particle', label='Particle Radius'),
            Item('r_platform', label='Platform Radius'),
            ),
        HGroup(
            Item('coverage', label='Disk Coverage %'),
            #Item('vinc_occ', label='Volume of inclusions', style='readonly') ),
            Item('N_occ', label='Occupied Sites     '), 
            Item('N_tot', label='Total Sites', style='readonly')
            ),
        HGroup(
            Item('vshell_occ', label='Shell volume occupied'), 
            Item('VT', label='Total shell volume', style='readonly')
            ),
        Include('mixgroup'),
        label='Layer Inclusions and Mixing'    )

    traits_view=View(
        #	Include('compmatgroup'),
        Include('inclusionsgroup')
    )

class TriangularInclusions(CompositeMaterial):
    '''Essentially a composite material except inclusions of triangular cylinder are integrated with the VFrac parameter in volume'''
    ###Here we also look into the equilateral triangular particles, this model is given by the paper "Adsorption and Conformation of Serum Albumin Protein on Gold Nanoparticles Investigated Using Dimensional Measurements and in Situ Spectroscopic Methods" by Tsai and DelRio etc.###

    platform_type=Str
    particle_type=Str('Triangular Inclusions')  
    mat_name=Str('Composite Material with Triangular Inclusions')

    l_particle=Float(8.0)   #the edge length of the triangular particle   
    h_particle=Float(3.0)   #the thickness of the triangular particle
    r_platform=Float(12.0)  #the radius of the spherical np particle core
    shell_width=Property(Float, depends_on='l_particle, h_particle')  #Thickness of shell determined by 2r inclusion

    vbox=Property(Float, depends_on='l_particle, h_particle')      #Rectangular box volume determined by the triangular particle
    unitvolume=Property(Float, depends_on='l_particle, h_particle')   #Total amount of volume occupied by the triangular particle 
    VT=Property(Float, depends_on='l_particle, h_particle, r_platform') #DEFINED SEPARATELY FOR DIFFERENT SHELL CASES

    N_tot=Property(Float, depends_on='VT, vbox')
    N_occ=Property(Float, depends_on='Vfrac, VT, unitvolume')

    vinc_occ=Property(Float, depends_on='N_occ, unitvolume')  #Total volume of the inclusions
    vshell_occ=Property(Float, depends_on='N_occ, vbox')      #Total volume of the shell filled by boxes

    coverage=Property(Float, depends_on='N_occ, N_tot')

    def __init__(self, *args, **kwargs):
        super(TriangularInclusions, self).__init__(*args, **kwargs)


    def _get_vbox(self):
        return (self.l_particle**2)*self.h_particle         #Square boxes of volumes

    def _get_vinc_occ(self): 
        return self.N_occ*self.unitvolume

    def _get_vshell_occ(self): 
        return self.N_occ*self.vbox

    def _get_unitvolume(self): 
        value= math.sqrt(3)*(self.l_particle**2)*self.h_particle/4.0  #THIS IS ONLY VALID FOR TRIANGULAR CYLINDER
        return round(value, 2)

    def _get_N_tot(self):
        return int(self.VT/self.vbox)   #Total number of available boxes is Vbox/VT

    def _get_N_occ(self): 
        return int((self.Vfrac * self.VT)/(self.unitvolume))

    def _set_N_occ(self, Nocc): 
        self.Vfrac= (Nocc * self.unitvolume)/self.VT 

    def _get_coverage(self): 
        return round ( (float(self.N_occ) / float(self.N_tot) )*100.0 , 4)	
    
    def _set_coverage(self, coverage):
        self.N_occ=int( (coverage * self.N_tot) / 100.0	)

class TriangularInclusions_Shell_case1(TriangularInclusions):
    '''Used for sphere/shell nanoparticles; shell thickness is determined by l_particle (edge length of the triangular cylinder)'''

    platform_type=Str('Shell Platform')   #Core particle  (Usually NP)
    mat_name=Str('Triangular Inclusions (orientation1) on a Spherical particle"s shell')


    inclusionsgroup=Group(
        HGroup(Item('particle_type', style='readonly'), Item('platform_type', style='readonly')), 
        HGroup( Item('l_particle', label='Inclusion edge length'), Item('h_particle', label='Inclusion height'), 
                Item('shell_width', style='readonly')), (Item('r_platform')),
        HGroup(Item('coverage', label='Shell Coverage %'),Item('vinc_occ', label='Total inclusion volume') ),
        HGroup(Item('N_occ', label='Occupied Sites     '), Item('N_tot', label='Total Sites')),
        HGroup(Item('vshell_occ', label='Shell volume occupied'), Item('VT', label='Total shell volume')),
        Include('mixgroup'),
        label='Shell Inclusions and Mixing'    )

    traits_view=View(
        Include('compmatgroup'), Include('inclusionsgroup')
    )

    #@cached_property
    def _get_shell_width(self): return self.l_particle

    #@cached_property
    def _get_VT(self): return round ( (4.0*math.pi/3.0) * (  (self.r_platform+2.0*self.l_particle)**3 - self.r_platform**3 ) , 2)

class TriangularInclusions_Shell_case2(TriangularInclusions):
    '''Used for sphere/shell nanoparticles; shell thickness is determined by h_particle (height of the triangular cylinder)'''

    mat_name=Str('Triangular Inclusions (orientation 2) on a Spherical particle"s shell')

    platform_type=Str('Shell Platform')   #Core particle  (Usually NP)

    inclusionsgroup=Group(
        HGroup(Item('particle_type', style='readonly'), Item('platform_type', style='readonly')), 
        HGroup( Item('l_particle', label='Inclusion edge length'), Item('h_particle', label='Inclusion height'), Item('shell_width', style='readonly')), (Item('r_platform')),
        HGroup(Item('coverage', label='Shell Coverage %'),Item('vinc_occ', label='Total inclusion volume') ),
        HGroup(Item('N_occ', label='Occupied Sites     '), Item('N_tot', label='Total Sites')),
        HGroup(Item('vshell_occ', label='Shell volume occupied'), Item('VT', label='Total shell volume')),
        Include('mixgroup'),
        label='Shell Inclusions and Mixing'    )

    traits_view=View(
        Include('compmatgroup'), Include('inclusionsgroup')
    )

    #@cached_property
    def _get_shell_width(self): return self.h_particle

    #@cached_property
    def _get_VT(self): return round ( (4.0*math.pi/3.0) * (  (self.r_platform+2.0*self.h_particle)**3 - self.r_platform**3 ) , 2)



if __name__ == '__main__':
#	f=CompositeMaterial_Equiv()
    f=TriangularInclusions_Shell_case1()
#	f=SphericalInclusions_Disk()
    f.configure_traits()