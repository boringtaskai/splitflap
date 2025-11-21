#!/usr/bin/env python3

#   Copyright 2020 Scott Bezek and the splitflap contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from __future__ import division
from __future__ import print_function

import argparse
import logging
import os
import subprocess
import sys

from svg_processor import SvgProcessor
from projection_renderer import Renderer

script_dir = os.path.dirname(os.path.abspath(__file__))
source_parts_dir = os.path.dirname(script_dir)
repo_root = os.path.dirname(source_parts_dir)
sys.path.append(repo_root)

from util import (
    app_paths,
    inkscape,
    rev_info,
)

_MODES = {
    'double-sided': 0,
    'front-back': 1,
    'full-font': 2,
    'side-by-side': 3,
    'full-font-pvc': 4,
}

def render(extra_variables, skip_optimize, output_directory, render_raster, color_inverted):
    logging.info('Start: ' + str(color_inverted))
    renderer = Renderer(os.path.join(source_parts_dir, 'font_generator_custom.scad'), output_directory, color_inverted, extra_variables)
    renderer.clean()
    svg_output, _ = renderer.render_svgs(panelize_quantity = 1)

    processor = SvgProcessor(svg_output)

    if not skip_optimize:
        logging.info('Removing redundant lines')
        processor.remove_redundant_lines()

    processor.write(svg_output)
    logging.info('\n\n\nDone rendering to SVG: ' + svg_output)

    if render_raster:
        # Export to png
        logging.info('Generating raster preview')
        raster_png = os.path.join(output_directory, 'raster.png')

        logging.info('Export PNG')
        subprocess.check_call([
            app_paths.get('inkscape'),
            '--export-width=1080',
            '--export-background=white',
        ] + inkscape.export_png(raster_png) + [
            svg_output,
        ])


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()

    parser.add_argument('--mode', choices=_MODES.keys(), required=True)
    parser.add_argument('--render-raster', action='store_true', help='Render raster PNG from the output SVG (requires '
                                                                     'Inkscape)')

    parser.add_argument('-f', '--font', type=str, help='Name of font preset to use - see flap_fonts.scad')
    parser.add_argument('-t', '--text', type=str, help='String of text to generate')

    parser.add_argument('--columns', type=int, help='Number of columns')
    parser.add_argument('--start-row', type=int, help='The starting row to render, 0-indexed')
    parser.add_argument('--row-count', type=int, help='Number of rows to render')

    parser.add_argument('--spacing-x', type=float, help='Horizontal gap between flaps')
    parser.add_argument('--spacing-y', type=float, help='Vertical gap between flaps')

    parser.add_argument('--no-comp', action='store_true', default=False, help='Don\'t compensate for the gap between top and bottom flaps')
    parser.add_argument('--alignment', action='store_true', help='Render alignment markers for registration when printing onto flaps')

    parser.add_argument('--bleed', type=float, help='Bleed amount for letters, in mm')
    parser.add_argument('--kerf', type=float, help='Override kerf_width value')
    parser.add_argument('--fill', action='store_true', help='Fill the text solid (disables optimization)')
    parser.add_argument('--skip-optimize', action='store_true', help='Don\'t remove redundant/overlapping cut lines')
    parser.add_argument('--vertical-keepout-clip', action='store_true', help='Clip letters that violate vertical keepout zones')
    parser.add_argument('--all-individual', action='store_true', help='Work for full-font-pvc mode, to print all the characters but only per')
    parser.add_argument('--color-inverted', action='store_true', help='If color-inverted, then the background will be black and the font will be white')

    args = parser.parse_args()

    extra_variables = {
        'render_revision': rev_info.git_short_rev(),
        'render_date': rev_info.current_date(),
        'letter_gap_comp' : not args.no_comp,
    }
    if args.font is not None:
        extra_variables['font_preset'] = args.font
    if args.text is not None:
        extra_variables['character_list'] = args.text

    if args.start_row is not None:
        extra_variables['start_row'] = args.start_row
    if args.row_count is not None:
        extra_variables['row_count'] = args.row_count
    if args.columns is not None:
        extra_variables['num_columns'] = args.columns

    if args.spacing_x is not None:
        extra_variables['spacing_x'] = args.spacing_x
    if args.spacing_y is not None:
        extra_variables['spacing_y'] = args.spacing_y

    if args.kerf is not None:
        extra_variables['kerf_width'] = args.kerf
    if args.fill:
        extra_variables['render_fill'] = True
        args.skip_optimize = True
    if args.bleed is not None:
        extra_variables['bleed'] = args.bleed

    if args.vertical_keepout_clip:
        extra_variables['vertical_keepout_mode'] = 2
   

    fonts_directory = os.path.join(source_parts_dir, 'build', 'fonts')

    extra_variables['layout_mode'] = _MODES[args.mode]
    
    if args.mode in ['double-sided', 'front-back']:
        if args.all_individual:
            raise RuntimeError('--all-individual argument only for full-font-pvc mode, please remove the argument if you use other mode.')
         
        extra_variables['render_alignment_marks'] = args.alignment

        extra_variables['only_side'] = 1
        extra_variables['flip_entire_layout'] = False
        extra_variables['flip_individual_flaps'] = False
        render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'front'), args.render_raster, args.color_inverted)

        extra_variables['only_side'] = 2
        if args.mode == 'double-sided':
            extra_variables['flip_entire_layout'] = True     # if true, then the layout will be flip from the right to left - valle
            extra_variables['flip_individual_flaps'] = False # if true, the character will be mirror - valle
        elif args.mode == 'front-back':
            extra_variables['flip_entire_layout'] = False    # if true, then the layout will be flip from the right to left
            extra_variables['flip_individual_flaps'] = True  # if true, the character will be mirror - valle
        render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'back'), args.render_raster, args.color_inverted)
    elif args.mode in ['full-font-pvc']:
        if args.alignment:
            raise RuntimeError('Alignment markers are only compatible with double-sided rendering')
        
        if args.row_count % 2 == 1 or args.row_count == 0:
            raise RuntimeError('For full-font-pvc mode the --row-count should be greater than 0 and multiple of 2.')
        
        if args.start_row % 2 == 1:
            raise RuntimeError('For full-font-pvc mode the --start-row should be greater than 0 and multiple of 2.')
        
        if not args.all_individual:
            extra_variables['only_side'] = 1
            extra_variables['flip_entire_layout'] = False
            render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'front'), args.render_raster, args.color_inverted)

            extra_variables['only_side'] = 2
            extra_variables['flip_entire_layout'] = False    # if true, then the layout will be flip from the right to left
            extra_variables['flip_individual_flaps'] = True  
            render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'back'), args.render_raster, args.color_inverted)     
        else:
            num_flaps = 52
            extra_variables['start_row'] = 0
            extra_variables['row_count'] = 2
            extra_variables['num_columns'] = 1
            extra_variables['render_etch'] = True

            for counter, i in enumerate(range(0, num_flaps, 2), start=1):
                extra_variables['start_row'] = i
                extra_variables['only_side'] = 1
                extra_variables['flip_entire_layout'] = False
                render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'card ' + str(counter),'front'), args.render_raster, args.color_inverted)

                extra_variables['only_side'] = 2
                extra_variables['flip_entire_layout'] = False    # if true, then the layout will be flip from the right to left
                extra_variables['flip_individual_flaps'] = True  
                render(extra_variables, args.skip_optimize, os.path.join(fonts_directory, 'card ' + str(counter), 'back'), args.render_raster, args.color_inverted)     

    else:
        if args.alignment:
            raise RuntimeError('Alignment markers are only compatible with double-sided rendering')

        extra_variables['only_side'] = 1
        extra_variables['flip_entire_layout'] = False
        render(extra_variables, args.skip_optimize, fonts_directory, args.render_raster, args.color_inverted)
