# The Newshub

_Consolidation task content for sphinx and docker also included_

A modern digital news platform built with **Django**, enabling **journalists**, **editors**, and **readers** to collaborate seamlessly in producing and consuming high-quality content.  
The platform includes full editorial workflows, role-based permissions, a RESTful API for integrations, and automated publishing through **Twitter/X** and email notifications.

## Core Features

### Articles & Newsletters

- Journalists can create, edit, and delete **articles** and **newsletters**.
- Editors can review, edit, approve, or reject submissions.
- Approved articles automatically:
  - trigger **email notifications** to subscribers, and
  - post updates to **X** via API integration.
- Articles display their relevent **status**
  - Draft
  - Pending Approval
  - Published
  - Rejected

### Publications

- Publications can have **multiple editors** and **journalists**.
- Journalists can **request to join** a publication; editors can approve or reject these requests.
- Editors manage all publication content and contributors from the **editor dashboard**.

### Subscription

- Readers can subscribe to:
  - a **Publication**, or
  - an independent **Journalist**.
- A Reader **cannot subscribe to both** if the journalist already writes exclusively for that publication.

### Custom User Roles

Custom roles determine access control and permissions:

**Reader**

- View and comment on published articles and newsletters
- Subscribe to journalists or publications
- Tate and comment on articles and newsletters

**Journalist**

- Create, edit, and delete own articles or newsletters
- Submit to publications for approval

**Editor**

- View, edit, approve, or reject all content for their publication(s)
- Manage join requests and publication details

Each user is automatically assigned to the relevant **Group** based on their role and given respective **permissions**.

## Tech Stack

- **Backend:** Django 5, Django REST Framework (DRF)
- **Frontend:** HTML, CSS, Bootstrap, JavaScript
- **Database:** MariaDB
- **External Integrations:** Twitter API (via Tweepy)

## Models

Below are my models used which did differ slightly from my original planning.

### User Model

```
class User(AbstractUser):
    ROLE_CHOICES = [
        ("reader", "Reader"),
        ("journalist", "Journalist"),
        ("editor", "Editor")
        ]
    username = None
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="reader"
        )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    display_name = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Optional name for comments")
    subscribed_publishers = models.ManyToManyField(
        "publications.Publication", related_name="subscribed_readers",
        blank=True,  help_text="Publishers this reader follows",
        )
    subscribed_journalists = models.ManyToManyField(
        "self", symmetrical=False, related_name="reader_followers",
        blank=True, help_text="Journalists this reader follows",
        )
    independent_articles = models.ManyToManyField(
        "articles.Article", related_name="independent_authors",
        blank=True,
        help_text="Articles published independently by this journalist",
        )
```

### Subscription

```
class Subscription(models.Model):
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="subscriptions"
        )
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="subscriptions",
        )
    journalist = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="journalist_subscriptions",
        )
    created_at = models.DateTimeField(auto_now_add=True)
```

### Publication

```
class Publication(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    editors = models.ManyToManyField(
        User, related_name="edited_publications", blank=True
    )
    journalists = models.ManyToManyField(
        User, related_name="joined_publications", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
```

### Journalist Join Request

```
class JoinRequest(models.Model):
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="join_requests"
        )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="publication_requests"
        )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ],
        default="pending",
        )
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
```

### Article

```
class Article(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("published", "Published"),
        ("rejected", "Rejected"),
        ]

    TYPE_CHOICES = [
        ("article", "Article"),
        ("newsletter", "Newsletter"),
        ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="articles"
        )
    publication = models.ForeignKey(
        "publications.Publication", on_delete=models.CASCADE,
        related_name="articles", null=True, blank=True,
        )
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="article",
        help_text=("Choose 'Article' for multi-block content, "
                   "or 'Newsletter' for simple text content.")
        )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
        )
    content = CKEditor5Field("Content", config_name="default", blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
```

### Comments

```
class Comment(models.Model):
    article = models.ForeignKey(
        Article, related_name="comments", on_delete=models.CASCADE
        )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### ratings

```
class Rating(models.Model):
    article = models.ForeignKey(
        Article, related_name="ratings", on_delete=models.CASCADE
        )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()
```

### Other Features

#### Signals & Automation

Implemented via Django signals:

- When an article is **approved and published**, signals trigger:
  - A **Tweet** to the configured X/Twitter account
  - An **email notification** to all relevant subscribers

#### RESTful API

The platform exposes a secure **REST API** built with Django REST Framework and JWT authentication.

## Front-End Integration

### CKEditor 5

- Used for rich article editing with image upload and alignment options.
- Journalists can easily format content with consistent styling matching the site’s design.
- Images are handled via CKEditor’s built-in upload adapter.

### Crispy Forms (Bootstrap 5)

- Provides clean, responsive form layouts throughout the site.
- Used for article creation, publication management, and user requests.

### 📬 Email & Twitter Integration

- **Email**: Uses Django’s `send_mail` for subscriber notifications.  
  Requires a configured SMTP or console backend (for development).
- **Twitter/X**: Integrated via the Tweepy library and the Twitter API, allowing automatic posting of approved articles.

## Setup & Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/thenewshub.git
   cd thenewshub
   ```

2. Create and activate virtual environment

```
python -m venv .venv
source .venv/bin/activate  # (Linux/Mac)
.venv\Scripts\activate     # (Windows)
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Apply migrations

```
python manage.py migrate
```

5. Create a superuser

```
python manage.py createsuperuser
```

6. Run the development server

```
python manage.py runserver
```

## Possible Future Enhancements

Features that I could have added or would have added if I had more time.

- Extend CKEditor configuration for captioned and side-aligned images
- Enable popup notifications
- Implement in-app notifications for approvals and feedback
- Image thumbnails for content card
- Tagline in content cards
- Enable role switching - reader become journalist/editor

## Acknowledgements

- **[Django](https://docs.djangoproject.com/en/5.2/)** documentation
- **[bootstrap 5](https://getbootstrap.com/)**
- **[Google Fonts](https://fonts.google.com/)**
- **[Font Awesome](https://fontawesome.com/)**
- **[Stack Overflow](stackoverflow.com)**
- **[W3 Schools](w3schools.com)**
- **[Geeksforgeeks](geeksforgeeks.org/)**
- **[PlantUML](https://editor.plantuml.com/)**
- **[draw.io](https://www.drawio.com/)**

## Consolidation

## Sphinx Docstrings

As per the consolidationtask, I have added Sphinx docstrings to **articles/views.py** and **publications/views.py**

The index.html file can be found in docs/\_build/index.html.

### Adding Sphinx

- Install Sphinx

```
pip install sphinx
```

- Install Sphinx theme _(optional)_

```
pip install sphinx-rtd-theme
```

- When prompted
  - if you want to separate source and build directories, press enter to choose no (default)
  - enter a project name
  - provide authour name _<your_name>_
  - enter 00.00.01 for project release
  - press enter to choose default English language
- Open conf.py _docs/conf.py_ near the top add

```
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
```

- Locate the empty extensions list and add

```
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon"
]
```

- Then find html*theme and add *(if installed)\_

```
html_theme = 'sphinx_rtd_theme'
```

- Update docstring to sphinx format, _example_

```
class PublicationListView(ListView, PaginationMixin):
    """Display a paginated list of all publications.

    Combines standard list rendering with pagination to efficiently
    display publication entries.
    """
    model = Publication
    template_name = "publications/publication_list.html"
    context_object_name = "publications"

    def get_queryset(self):
        """Retrieve all publications and mark whether the logged-in journalist
        has a pending join request for each.

            :return: QuerySet of publications with a custom attribute
             has_pending_request added for the current user.
            :rtype: QuerySet
        """
        set = Publication.objects.prefetch_related("editors", "join_requests")
        user = self.request.user
        for pub in set:
            pub.has_pending_request = (
                pub.join_requests.filter(user=user, status="pending").exists()
                if user.is_authenticated and user.role == "journalist"
                else False
            )
        return set
```

- CD to project root _(should contain docs and your project folders)_
- Run command

```
sphinx-apidoc -o docs maths/
```

- If ran correctly, in your docs folder you will find a _projectname_.rst file.
- Locate the **index.rst** file and add **modules** below :caption: Content:
- CD into the docs folder and run

```
make html
```

- If succsess, in docs/\_build/html you will find **index.html** will docstrings included.

## Docker

A Dockerfile was create to contain my capstone project and successfully tested on Docker Playground.

To verify, ensure you're in the right directory _the_newshub_ then follow the below.

- Visit [Docker Playground](https://labs.play-with-docker.com/) and log in.
- Press start, then Add New Instance
- Clone the repository from [The Newshub](https://github.com/anthonyjn08/newshub/tree/main)

```
git clone https://github.com/...
```

- Build the coontaint

```
docker compose up -=build
```

- Once message confirms server has started click OPEN PORT enter 8000, click open to be taken to the site.

```

If for some reason, the database doesnt start, which is something that painfully happened to me, below are some instructiosn to manually build and start the services.

```

_#Clean and rebuild image_

docker compose down -v
docker compose build

_# Start the database_

docker compose up -d db

_# run migrations_

docker compose run --rm web python manage.py migrate

_# start the web process_

docker compose up

_# service running when you see_

web-1 | Django version X.X.X, using settings 'the_newshub.settings'

web-1 | Starting development server at http://0.0.0.0:8000/

```

```
