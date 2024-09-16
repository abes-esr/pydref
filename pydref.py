import requests
import unicodedata
import string
from bs4 import BeautifulSoup
import datetime
from retry import retry

NOT_SCIENTIST_TOKEN = ['chanteur', 'dramaturge', 'journalist', 'poete', 'theater', 'theatre']


@retry(delay=200, tries=5)
def get_url(url, params={}, headers={}, timeout=2):
    return requests.get(url, params=params, headers=headers, timeout=timeout)

def strip_accents(w: str) -> str:
    """Normalize accents and stuff in string."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', w)
        if unicodedata.category(c) != 'Mn')


def delete_punct(w: str) -> str:
    """Delete all punctuation in a string."""
    return w.lower().translate(
        str.maketrans(string.punctuation, len(string.punctuation) * ' '))

def normalize(x):
    x = x.replace('\xa0', ' ')
    return strip_accents(delete_punct(x)).lower().strip()

class Pydref(object):
    """ Wrapper around the PubMed API.
    """

    def __init__(
        self: object
    ) -> None:
        """ Initialization of the object.
            Parameters:
                - None
            Returns:
                - None
        """

        # Store the parameters
        self.timeout = 2


    def query(self: object, query: str):
        """ Method that executes a query agains the idref Solr
            inserting the PubMed data loader.
            Parameters:
                - query     String
            Returns:
                - result    solr output
        """

        solr_query = " AND ".join(query.split(' '))
        params = {'q': 'persname_t: ({})'.format(solr_query),
                  'wt': 'json',
                  'fl': '*',
                  'sort': 'score desc',
                  'version': '2.2'
                  }
  
        r = get_url(
                    "https://www.idref.fr/Sru/Solr",
                    params=params,
                    headers=None,
                    timeout=self.timeout)
        if r.status_code == 200 and r.text:
            return r.json()
        return {"error": r.text}
    
    def get_idref_notice(self: object, idref: str):
        """ Method that downloads the xml notice of a given idref
        """
        try: 
            r = get_url("https://www.idref.fr/{}.xml".format(idref))
            if r.status_code != 200:
                print("Error in getting notice {} : {}".format(idref, r.text))
                return {}
            return r.text
        except:
            print("Error in getting notice {}".format(idref))
            return {}
    
    
    def get_idref(self: object, query: str, min_birth_year, min_death_year, is_scientific, exact_fullname):
        """ Method that first permorf a query and then parses the main infos of the results
        """
        
        res = self.query(query)
        
        possible_match = []

        for d in res.get('response', {}).get('docs', []):
            if 'ppn_z' in d:
                person = {'idref' : "idref{}".format(d['ppn_z'])}
                notice = self.get_idref_notice(d['ppn_z'])
                if not notice:
                    continue
                soup = BeautifulSoup(notice, 'lxml')
                person_name = self.get_name_from_idref_notice(soup)
                person['last_name'] = person_name.get("last_name")
                person['first_name'] = person_name.get("first_name")
                person['full_name'] = f"{person['first_name']} {person['last_name']}".strip()
                person['full_name2'] = f"{person['last_name']} {person['first_name']}".strip()
                exact_fullname = [normalize(person['full_name']), normalize(person['full_name2'])]

                if normalize(query) not in exact_fullname:
                    print(f'no exact fullname match for {query} vs {exact_fullname}')
                    continue
                birth, death = self.get_birth_and_death_date_from_idref_notice(soup)
                if birth:
                    person['birth_date'] = birth
                if death:
                    person['death_date'] = death

                if birth and int(birth[0:4]) < min_birth_year:
                    print(f'skipping birth date {birth}')
                    continue
                
                if death and int(death[0:4]) < min_death_year:
                    print(f'skipping death date {death}')
                    continue

                identifiers = self.get_identifiers_from_idref_notice(soup)
                person['identifiers'] = identifiers

                skip = False
                person['description'] = self.get_description_from_idref_notice(soup)
                if is_scientific:
                    for d in person['description']:
                        for w in NOT_SCIENTIST_TOKEN:
                            if w in d.lower():
                                skip = True
                                print(f'skipping {d}')
                                break
                if skip:
                    continue

                person['gender'] = self.get_gender(soup)

                possible_match.append(person)
        return possible_match
    
    def identify(self: object, query: str, min_birth_year = 1920, min_death_year = 2005, is_scientific = True, exact_fullname = True):
        """ Method that try to identify an idref from a simple input
            Return a match only if the solr engine gives exactly one result
        """
        
        all_idref = self.get_idref(query, min_birth_year, min_death_year, is_scientific, exact_fullname)
        if len(all_idref) == 1:
            res = all_idref[0].copy()
            res['status'] = 'found'
            res['nb_homonyms'] = len(all_idref)
            return res
        else:
            res = {}
            res['nb_homonyms'] = len(all_idref)
            if len(all_idref) == 0:
                res['status'] = 'not_found'
            elif len(all_idref) > 1:
                res['status'] = 'not_found_ambiguous'
            return res
        return {}

    def keep_digits(self: object, x: str) -> str:
        """Extract digits from string."""
        return str("".join([c for c in x if c.isdigit()]).strip())

    def valid_idref_date(self: object, x: str):
        """Keep date only if it is a valid year (YYYY) or a valid YYYYMMDD."""
        if len(x) != len(self.keep_digits(x)):
            return None
        if len(x) not in [4, 8]:
            return None

        year = int(x[0:4])
        try:
            month = int(x[4:6])
        except Exception:
            month = 1

        try:
            day = int(x[6:8])
        except Exception:
            day = 1

        try:
            date_str = datetime.datetime(year, month, day).isoformat()
        except Exception:
            print("weird date input {}".format(x))
            date_str = datetime.datetime(year, 1, 1).isoformat()
        return date_str

    def get_name_from_idref_notice(self: object, soup):
        """Get Name from notice."""
        current_name, current_first_name = None, None
        for datafield in soup.find_all("datafield"):
            if (datafield.attrs['tag'] in ['200']):
                current_name, current_first_name = '', ''
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        current_name = subfield.text
                    if subfield.attrs['code'] == 'b':
                        current_first_name = subfield.text
        return {"last_name": current_name, "first_name": current_first_name}

    def get_birth_and_death_date_from_idref_notice(self: object, soup):
        """Get birth and death dates from notice."""
        birth, death = None, None
        for datafield in soup.find_all("datafield"):
            if (datafield.attrs['tag'] == '103'):
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        birth = self.valid_idref_date(subfield.text.strip())
                    if subfield.attrs['code'] == 'b':
                        death = self.valid_idref_date(subfield.text.strip())
        return (birth, death)

    def get_identifiers_from_idref_notice(self: object, soup):
        """Get all other identifiers from notice."""
        identifiers = []

        for controlfield in soup.find_all("controlfield"):
            if (controlfield.attrs['tag'] == '001'):
                identifiers.append({'idref': controlfield.text.strip()})
                break

        for datafield in soup.find_all("datafield"):

            if (datafield.attrs['tag'] == '010'):
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        identifiers.append({'isni': subfield.text.strip()})
                        break

            if (datafield.attrs['tag'] == '033'):
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        identifiers.append({'ark': subfield.text.strip()})
                        break

            if (datafield.attrs['tag'] == '035'):
                is_ORCID = False
                for subfield in datafield.findAll("subfield"):
                    if subfield.text.strip().upper() == 'ORCID':
                        is_ORCID = True
                        break
                if(is_ORCID):
                    for subfield in datafield.findAll("subfield"):
                        if subfield.attrs['code'] == 'a':
                            identifiers.append({'orcid': subfield.text.strip()})
                            break

            if (datafield.attrs['tag'] == '035'):
                is_sudoc = False
                for subfield in datafield.findAll("subfield"):
                    if subfield.text.strip().upper() == 'SUDOC':
                        is_sudoc = True
                        break
                if(is_sudoc):
                    for subfield in datafield.findAll("subfield"):
                        if subfield.attrs['code'] == 'a':
                            identifiers.append({'sudoc': subfield.text.strip()})
                            break
        return identifiers

    def get_description_from_idref_notice(self: object, soup):
        """Get person's description from notice."""
        descriptions = []
        for datafield in soup.find_all("datafield"):
            if (datafield.attrs['tag'] == '340'):
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        descriptions.append(subfield.text.strip())
        return descriptions


    def get_gender(self: object, soup):
        """Get gender from notice."""
        for datafield in soup.find_all("datafield"):
            if (datafield.attrs['tag'] == '120'):
                for subfield in datafield.findAll("subfield"):
                    if subfield.attrs['code'] == 'a':
                        subfield_value = subfield.text.strip()
                        if subfield_value == 'aa':
                            return 'F'
                        elif subfield_value == 'ba':
                            return 'M'
        return None
