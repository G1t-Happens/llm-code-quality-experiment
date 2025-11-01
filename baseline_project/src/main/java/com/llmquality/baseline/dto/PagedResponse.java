package com.llmquality.baseline.dto;

import org.springframework.data.domain.Page;

import java.util.List;


/**
 * Generic pagination DTO for REST API responses.
 *
 * <p>This DTO encapsulates paginated content along with metadata
 * about the current page, page size, total elements, total pages,
 * and whether the current page is the last one.</p>
 *
 * <p>This class provides a static factory method {@link #fromPage(Page)}
 * to easily convert a {@link Page} from Spring Data JPA into a stable
 * response structure suitable for REST APIs.</p>
 *
 * @param <T> the type of content in the page
 */
public record PagedResponse<T>(
        List<T> content,
        int page,
        int size,
        long totalElements,
        int totalPages,
        boolean last
) {

    /**
     * Creates a {@code PagedResponse} from a Spring Data {@link Page}.
     *
     * @param page the {@link Page} containing content and pagination metadata
     * @param <T>  the type of the content
     * @return a new {@link PagedResponse} with content and pagination info
     */
    public static <T> PagedResponse<T> fromPage(Page<T> page) {
        return new PagedResponse<>(
                page.getContent(),
                page.getNumber(),
                page.getSize(),
                page.getTotalElements(),
                page.getTotalPages(),
                page.isLast()
        );
    }
}
