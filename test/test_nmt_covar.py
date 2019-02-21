import unittest 
import numpy as np
import pymaster as nmt
import healpy as hp
import warnings
import sys
from .testutils import normdiff, read_flat_map

#Unit tests associated with the NmtField and NmtFieldFlat classes

class TestCovarFsk(unittest.TestCase) :
    def setUp(self) :
        wcs,msk=read_flat_map("test/benchmarks/msk_flat.fits")
        (ny,nx)=msk.shape
        lx=np.radians(np.fabs(nx*wcs.wcs.cdelt[0]))
        ly=np.radians(np.fabs(ny*wcs.wcs.cdelt[1]))
        mps=np.array([read_flat_map("test/benchmarks/mps_flat.fits",i_map=i)[1] for i in range(3)])

        d_ell=20;
        lmax=500.;
        ledges=np.arange(int(lmax/d_ell)+1)*d_ell+2
        self.b=nmt.NmtBinFlat(ledges[:-1],ledges[1:])
        ledges_half=ledges[:len(ledges)//2]
        self.b_half=nmt.NmtBinFlat(ledges_half[:-1],ledges_half[1:])
        self.f0=nmt.NmtFieldFlat(lx,ly,msk,[mps[0]])
        self.f2=nmt.NmtFieldFlat(lx,ly,msk,[mps[1],mps[2]])
        self.f0_half=nmt.NmtFieldFlat(lx,ly,msk[:ny//2,:nx//2],
                                      [mps[0,:ny//2,:nx//2]])
        self.w=nmt.NmtWorkspaceFlat()
        self.w.read_from("test/benchmarks/bm_f_nc_np_w00.dat")
        
        l,cltt,clee,clbb,clte,nltt,nlee,nlbb,nlte=np.loadtxt("test/benchmarks/cls_lss.txt",unpack=True)
        self.l=l
        self.cltt=cltt+nltt
        
    def test_workspace_covar_flat_benchmark(self) :
        cw=nmt.NmtCovarianceWorkspaceFlat()
        cw.compute_coupling_coefficients(self.f0,self.f0,self.b)

        covar=nmt.gaussian_covariance_flat(cw,0,0,0,0,self.l,
                                           [self.cltt],[self.cltt],[self.cltt],[self.cltt],
                                           self.w)
        covar_bench=np.loadtxt("test/benchmarks/bm_f_nc_np_cov.txt",unpack=True)
        self.assertTrue((np.fabs(covar-covar_bench)<=np.fmin(np.fabs(covar),np.fabs(covar_bench))*1E-5).all())

    def test_workspace_covar_flat_errors(self) :
        cw=nmt.NmtCovarianceWorkspaceFlat()

        with self.assertRaises(ValueError) : #Write uninitialized
            cw.write_to("wsp.dat");
        
        cw.compute_coupling_coefficients(self.f0,self.f0,self.b)  #All good
        self.assertEqual(cw.wsp.bin.n_bands,self.w.wsp.bin.n_bands)

        with self.assertRaises(RuntimeError) : #Write uninitialized
            cw.write_to("tests/wsp.dat");

        cw.read_from('test/benchmarks/bm_f_nc_np_cw00.dat') #Correct reading
        self.assertEqual(cw.wsp.bin.n_bands,self.w.wsp.bin.n_bands)

        #gaussian_covariance
        with self.assertRaises(ValueError) : #Wrong input power spectra
            nmt.gaussian_covariance_flat(cw,0,0,0,0,self.l,
                                         [self.cltt],[self.cltt],[self.cltt],[self.cltt[:15]],self.w)
        with self.assertRaises(ValueError) : #Wrong input power shapes
            nmt.gaussian_covariance_flat(cw,0,0,0,0,self.l,[self.cltt,self.cltt],
                                         [self.cltt],[self.cltt],[self.cltt[:15]],self.w)
        with self.assertRaises(ValueError) : #Wrong input spins
            nmt.gaussian_covariance_flat(cw,0,2,0,0,self.l,[self.cltt],
                                         [self.cltt],[self.cltt],[self.cltt],self.w)

        with self.assertRaises(RuntimeError) : #Incorrect reading
            cw.read_from('none')
        with self.assertRaises(ValueError) : #Incompatible resolutions
            cw.compute_coupling_coefficients(self.f0,self.f0_half,self.b)
        with self.assertRaises(RuntimeError) : #Incompatible bandpowers
            cw.compute_coupling_coefficients(self.f0,self.f0,self.b,self.f0,self.f0,self.b_half)

class TestCovarSph(unittest.TestCase) :
    def setUp(self) :
        #This is to avoid showing an ugly warning that has nothing to do with pymaster
        if (sys.version_info > (3, 1)):
            warnings.simplefilter("ignore", ResourceWarning)

        self.nside=64
        self.nlb=16
        self.npix=hp.nside2npix(self.nside)
        msk=hp.read_map("test/benchmarks/msk.fits",verbose=False)
        mps=np.array(hp.read_map("test/benchmarks/mps.fits",verbose=False,field=[0,1,2]))
        self.b=nmt.NmtBin(self.nside,nlb=self.nlb)
        self.f0=nmt.NmtField(msk,[mps[0]])
        self.f2=nmt.NmtField(msk,[mps[1],mps[2]])
        self.f0_half=nmt.NmtField(msk[:self.npix//4],[mps[0,:self.npix//4]]) #Half nside
        self.w=nmt.NmtWorkspace()
        self.w.read_from("test/benchmarks/bm_nc_np_w00.dat")
        
        l,cltt,clee,clbb,clte,nltt,nlee,nlbb,nlte=np.loadtxt("test/benchmarks/cls_lss.txt",unpack=True)
        self.l=l[:3*self.nside]
        self.cltt=cltt[:3*self.nside]+nltt[:3*self.nside]
                                                                                
    def test_workspace_covar_benchmark(self) :
        cw=nmt.NmtCovarianceWorkspace()
        cw.compute_coupling_coefficients(self.f0,self.f0)

        covar=nmt.gaussian_covariance(cw,0,0,0,0,[self.cltt],[self.cltt],[self.cltt],[self.cltt],self.w)
        covar_bench=np.loadtxt("test/benchmarks/bm_nc_np_cov.txt",unpack=True)
        self.assertTrue((np.fabs(covar-covar_bench)<=np.fmin(np.fabs(covar),np.fabs(covar_bench))*1E-4).all())

    def test_workspace_covar_errors(self) :
        cw=nmt.NmtCovarianceWorkspace()

        with self.assertRaises(ValueError) : #Write uninitialized
            cw.write_to("wsp.dat");
            
        cw.compute_coupling_coefficients(self.f0,self.f0) #All good
        self.assertEqual(cw.wsp.lmax,self.w.wsp.lmax)
        self.assertEqual(cw.wsp.lmax,self.w.wsp.lmax)
        with self.assertRaises(RuntimeError) : #Write uninitialized
            cw.write_to("tests/wsp.dat");

        cw.read_from('test/benchmarks/bm_nc_np_cw00.dat') #Correct reading
        self.assertEqual(cw.wsp.lmax,self.w.wsp.lmax)
        self.assertEqual(cw.wsp.lmax,self.w.wsp.lmax)

        #gaussian_covariance
        with self.assertRaises(ValueError) : #Wrong input power spectrum size
            nmt.gaussian_covariance(cw,0,0,0,0,[self.cltt],[self.cltt],
                                    [self.cltt],[self.cltt[:15]],self.w)
        with self.assertRaises(ValueError) : #Wrong input power spectrum shapes
            nmt.gaussian_covariance(cw,0,0,0,0,[self.cltt],[self.cltt],
                                    [self.cltt],[self.cltt,self.cltt],self.w)
        with self.assertRaises(ValueError) : #Wrong input spins
            nmt.gaussian_covariance(cw,0,2,0,0,[self.cltt],[self.cltt],
                                    [self.cltt],[self.cltt,self.cltt],self.w)
        
        with self.assertRaises(RuntimeError) : #Incorrect reading
            cw.read_from('none')

        with self.assertRaises(ValueError) : #Incompatible resolutions
            cw.compute_coupling_coefficients(self.f0,self.f0_half)
        
if __name__ == '__main__':
    unittest.main()
