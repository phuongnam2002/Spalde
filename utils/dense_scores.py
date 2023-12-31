import torch
from typing import List, Dict


def _build_index(activations: torch.Tensor, embeddings: torch.Tensor) -> List[dict]:
    index = []
    for tokens_activation, tokens_embeddings in zip(activations, embeddings):
        index.append(
            {
                token.item(): embedding
                for token, embedding in zip(tokens_activation, tokens_embeddings)
            }
        )

    return index


def _intersection(t1: torch.Tensor, t2: torch.Tensor) -> list:
    """
        Retrieve intersection between two tensors
        Return:
            List of elements appears in both that frequency >= 2
    """
    t1, t2 = t1.flatten(), t2.flatten()
    combined = torch.cat((t1, t2), dim=0)
    uniques, counts = combined.unique(return_counts=True, sorted=False)
    return uniques[counts > 1].tolist()


def _get_intersection(queries_activations: list, documents_activations: list) -> list:
    """
        Retrieve intersection of activated tokens between queries and documents
    """
    return [
        _intersection(query_activations, document_activations)
        for query_activations, document_activations in zip(
            queries_activations,
            documents_activations
        )
    ]


def _get_scores(
        anchor_embeddings_index: List[dict],
        positive_embeddings_index: List[dict],
        negative_embeddings_index: List[dict],
        positive_intersections: list,
        negative_intersections: list,
        func
) -> Dict[str, torch.Tensor]:
    """
        Computes similarity scores between queries and documents based on activated tokens embeddings
    """
    positive_scores, negative_scores = [], []

    for (
            anchor_embedding_index,
            positive_embedding_index,
            negative_embedding_index,
            positive_intersection,
            negative_intersection
    ) in zip(
        anchor_embeddings_index,
        positive_embeddings_index,
        negative_embeddings_index,
        positive_intersections,
        negative_intersections
    ):
        if len(positive_intersection) > 0 and len(negative_intersection) > 0:
            positive_scores.append(
                func(
                    torch.stack(
                        [
                            anchor_embedding_index[token]
                            for token in positive_intersection
                        ],
                        dim=0
                    )
                    * torch.stack(
                        [
                            positive_embedding_index[token]
                            for token in positive_intersection
                        ],
                        dim=0
                    )
                )
            )
            negative_scores.append(
                func(
                    torch.stack(
                        [
                            anchor_embedding_index[token]
                            for token in negative_intersection
                        ],
                        dim=0
                    )
                    * torch.stack(
                        [
                            negative_embedding_index[token]
                            for token in negative_intersection
                        ],
                        dim=0
                    )
                )
            )

    return {
        "positive_scores": torch.stack(positive_scores, dim=0) if len(positive_scores) > 0 else None,
        "negative_scores": torch.stack(negative_scores, dim=0) if len(negative_scores) > 0 else None
    }


def dense_scores(
        anchor_activations: torch.Tensor,
        positive_activations: torch.Tensor,
        negative_activations: torch.Tensor,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
        negative_embeddings: torch.Tensor,
        func=torch.sum
) -> Dict[str, torch.Tensor]:
    anchor_embeddings_index = _build_index(
        activations=anchor_activations, embeddings=anchor_embeddings
    )
    positive_embeddings_index = _build_index(
        activations=positive_activations, embeddings=positive_embeddings
    )

    negative_embeddings_index = _build_index(
        activations=negative_activations, embeddings=negative_embeddings
    )

    positive_intersections = _get_intersection(
        queries_activations=anchor_activations,
        documents_activations=positive_activations,
    )

    negative_intersections = _get_intersection(
        queries_activations=anchor_activations,
        documents_activations=negative_activations,
    )

    return _get_scores(
        anchor_embeddings_index=anchor_embeddings_index,
        positive_embeddings_index=positive_embeddings_index,
        negative_embeddings_index=negative_embeddings_index,
        positive_intersections=positive_intersections,
        negative_intersections=negative_intersections,
        func=func,
    )


def pairs_dense_scores(
        queries_activations: torch.Tensor,
        documents_activations: torch.Tensor,
        queries_embeddings: torch.Tensor,
        documents_embeddings: torch.Tensor
):
    """
        Scores pairs of queries and documents based on activated tokens
    """
    queries_embeddings_index = _build_index(
        activations=queries_activations, embeddings=queries_embeddings
    )

    documents_embeddings_index = _build_index(
        activations=documents_activations, embeddings=documents_embeddings
    )

    intersections = _get_intersection(
        queries_activations=queries_activations,
        documents_activations=documents_activations,
    )

    scores = []
    for (
            query_embeddings_index,
            document_embedding_index,
            intersection
    ) in zip(queries_embeddings_index, documents_embeddings_index, intersections):
        if len(intersection) > 0:
            scores.append(
                torch.sum(
                    torch.stack(
                        [query_embeddings_index[token] for token in intersection],
                        dim=0
                    )
                    * torch.stack(
                        [document_embedding_index[token] for token in intersection],
                        dim=0
                    )
                )
            )
        else:
            scores.append(torch.tensor(0.0, device=queries_activations.device))

    return torch.stack(scores, dim=0)
