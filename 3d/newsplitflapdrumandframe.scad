use<spool.scad>;
use<shapes.scad>;

include<flap_dimensions.scad>;
include<global_constants.scad>;
include<m4_dimensions.scad>;

use <flap.scad>


// original size

// num_flaps = 52;
// flap_hole_radius = 1.1;
// flap_hole_separation = 1.2;
// flap_spool_outset = 0.8;
// height = 3;

 
num_flaps = 52;
flap_hole_radius = 1.2;
flap_hole_separation = 1.2;
flap_spool_outset = 0.8;
height = 3;  // thickness of the material

echo(flap_pitch_radius = flap_pitch_radius);
 
//translate([-20, 0, 0])
//    flap_spool(num_flaps, flap_hole_radius, flap_hole_separation, flap_spool_outset, height);

// original size
//ECHO: flap_width = 54
//ECHO: flap_height = 43
//ECHO: flap_corner_radius = 3.1
//ECHO: eps = 0.01
//ECHO: flap_pin_width = 1.4
//ECHO: flap_notch_depth = 3.2
//ECHO: flap_notch_height = 15

//difference() {
//    union() {
//        square([flap_width, flap_height - flap_corner_radius]);
//
//        // rounded corners
//        hull() {
//            translate([flap_corner_radius, flap_height - flap_corner_radius])
//                circle(r=flap_corner_radius, $fn=40);
//                
//            translate([flap_width - flap_corner_radius, flap_height - flap_corner_radius])
//                circle(r=flap_corner_radius, $fn=40);
//        }
//    }
//    
//    // spool tabs
//    cut_tabs = true;
//    if(cut_tabs) {
//        translate([-eps, flap_pin_width])
//            square([eps + flap_notch_depth, flap_notch_height]);
//        translate([flap_width - flap_notch_depth, flap_pin_width])
//            square([eps + flap_notch_depth, flap_notch_height]);
//    }
//}
        

color([0,0,0]) {
    translate([flap_width, 0, 0]) { 
        flap_2d();
    }

    rotate([0, 0, 180])
    translate([-flap_width * 2, 3, 0]) { 
        flap_2d();
    } 
}


