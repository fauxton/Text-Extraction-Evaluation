'''
Helper script for generating meta data files and preprocessing datasets.

Throughout the script we're assuming the following structure 
of the directory that settings.PATH_LOCAL_DATA points to.

|-- datasets
|   |-- testdataset
|   |   |-- clean
|   |   |   `-- example.txt
|   |   |-- meta.yaml ----> this is where the output will reside
|   |   `-- raw
|   |       `-- example.html
|-- plot-output
|   `-- ...
`-- results-cache
    `-- ...
'''
import os
import sys
import re
import codecs
import logging

import yaml
from BeautifulSoup import BeautifulSoup
import argparse

import settings

class MetaGeneratorError(Exception):
    pass

class PreprocessingError(Exception):
    pass
    
def _verify_args(args):
    # verify arguments provoded by argparse and
    # return the path to the output directory
    
    # printing arguments
    print 'dataset type: %s' % args.dataset_type
    print 'dataset name: %s' % args.dataset_name
    
    #validate dataset name
    if not os.path.exists( os.path.join(settings.PATH_LOCAL_DATA, 'datasets', args.dataset_name)):
        print 'error: this dataset does not exist'
        sys.exit(-1)
    
    # validate path argument
    if args.path and not os.path.exists(args.path):
        print 'error: path does not exist'
        sys.exit(-1)
        
    output_dir = args.path or os.path.join(settings.PATH_LOCAL_DATA, 'datasets', args.dataset_name)
    print 'output directory: %s' % output_dir
    return output_dir

    
def _get_attribute(tag, name):
    # params: BS tag and attribute name
    # return None or attribute value
    # takes care of encoding
    try: 
        return tag[name].encode('ascii', 'ignore')
    except KeyError:
        return None

class CleanevalProcessor(object):
    
    def __init__(self, output_dir, dataset_name):   
        self._dataset_dir = os.path.join(settings.PATH_LOCAL_DATA,'datasets',dataset_name)
        self._output_dir = output_dir
        
    def create_backups(self):
        # rename every unprocessed [number].html to [number].html.backup 
        
        for raw_filename in os.listdir(os.path.join(self._dataset_dir, 'raw')):
            
            # validate raw filename names
            if not re.match(r'\d+.html', raw_filename):
                logging.warn('skipping file %s for not matching cleaneval naming convention', raw_filename)
                continue
            
            raw_filename_path = os.path.join(self._dataset_dir, 'raw', raw_filename)
            backup_path = raw_filename_path + '.backup'
            logging.info('renaming %s to %s', raw_filename, raw_filename + '.backup')
            os.rename(raw_filename_path, backup_path)
            
    def generate_meta_data(self):
        
        meta_data_list = [] # list to be serialized
        
        for raw_filename in os.listdir(os.path.join(self._dataset_dir, 'raw')):
      
            # validate raw names
            if not re.match(r'\d+.html.backup', raw_filename):
                raise MetaGeneratorError('Raw filename backup not matching [number].html.backup: %s' % raw_filename)
            
            with open(os.path.join(self._dataset_dir, 'raw', raw_filename), 'r' ) as f:
                
                # check for an existing clean file counterpart
                clean_filename = raw_filename.replace('.html.backup', '') + '-cleaned.txt'
                if not os.path.exists(os.path.join(self._dataset_dir, 'clean', clean_filename )):
                    raise MetaGeneratorError('No existing clean file counterpart for %s' % raw_filename)
                
                # get meta data from <text ...> tag
                soup = BeautifulSoup(f.read())
                text_tag = soup.find('text')
                if text_tag == None:
                    raise MetaGeneratorError('No <text> tag in %s' % raw_filename)
                encoding = text_tag['encoding']
                
                # extract dataset specific meta-data and store it into a dict with
                # keys id, title, encoding
                # since we'll be removing the <text> tag from every document
                # we better store this attributes in it's original form in meta.yaml
                cleaneval_specific = {
                    'id': _get_attribute(text_tag, 'id'),
                    'title': _get_attribute(text_tag, 'title'),
                    'encoding': _get_attribute(text_tag, 'encoding'),
                }
                
                # get a safe encoding name
                try:
                    codec = codecs.lookup(encoding)
                except LookupError:
                    safe_encoding = None
                else:
                    safe_encoding = codec.name
                    
                logging.info('generating meta data for %s', raw_filename)
                meta_data_list.append(dict(
                    url = None,
                    raw_encoding = safe_encoding,
                    # acording to anotation guidelines of cleaneval 
                    # all cleaned text files are utf-8 encoded
                    clean_encoding = 'utf-8',
                    # we'll be generating [number].html in the preprocessing phase
                    raw = raw_filename.replace('.backup', ''), 
                    clean = clean_filename,
                    meta = cleaneval_specific
                ))
                
        # dump meta data
        with open(os.path.join(self._output_dir, 'meta.yaml'), 'w') as meta_file:
            meta_string = yaml.dump(meta_data_list, default_flow_style=False) 
            meta_file.write(meta_string)
            
        

def main():
    # sys argument parsing trough argparse
    parser = argparse.ArgumentParser(description = 'Tool for generating meta data files and cleanup preprocessing regarding datasets')
    parser.add_argument('dataset_type', choices = ['cleaneval'], help = 'dataset type e.g. cleaneval' )# only cleaneval choice for now
    parser.add_argument('dataset_name', help = 'name of the dataset')
    parser.add_argument('-p','--path', help = 'path to the meta data output file and .log file (uses the default path if not provided)')
    args = parser.parse_args()
    
    # get the ouput direcotry - this is where the .yaml and .log file will reside
    output_dir = _verify_args(args)
    
    # now we can initialize logging
    print 'log: %s' % os.path.join(output_dir, 'preproc.log')
    logging.basicConfig(filename= os.path.join(output_dir, 'preproc.log'), level=logging.DEBUG)
    
    if args.dataset_type == 'cleaneval':
        processor = CleanevalProcessor(output_dir, args.dataset_name)
        print '[CREATE BACKUPS]'
        processor.create_backups()
        print '[GENERATING META DATA]'
        try:
            processor.generate_meta_data()
        except MetaGeneratorError as e:
            print e
            sys.exit(-1)
    print '[DONE]'
    
    
if __name__ == '__main__':
    main()

